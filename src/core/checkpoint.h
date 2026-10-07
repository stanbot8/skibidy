#ifndef CHECKPOINT_H_
#define CHECKPOINT_H_

// Verified replay restores all owners (including private scheduler and operation
// state) by rerunning the exact prefix. This provides no computation speedup.
#include <charconv>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <omp.h>
#include <TBufferFile.h>
#include "biodynamo.h"
#include "core/derived_field.h"
#include "core/treatment_schedule.h"

namespace bdm {
namespace skibidy {
namespace checkpoint {

constexpr uint64_t kHashBasis = 14695981039346656037ULL;
constexpr uint64_t kMaxConfigBytes = 16 * 1024 * 1024;

inline void HashBytes(uint64_t& hash, const void* data, size_t size) {
  const auto* bytes = static_cast<const unsigned char*>(data);
  for (size_t i = 0; i < size; ++i) {
    hash ^= bytes[i];
    hash *= 1099511628211ULL;
  }
}
template <typename T>
inline void HashObject(uint64_t& hash, const T& object) {
  HashBytes(hash, &object, sizeof(object));
}
inline std::string ReadFile(const std::string& path, uint64_t limit) {
  std::ifstream file(path, std::ios::binary | std::ios::ate);
  if (!file) throw std::runtime_error("cannot read checkpoint input: " + path);
  const auto size = file.tellg();
  if (size < 0 || static_cast<uint64_t>(size) > limit) {
    throw std::runtime_error("invalid checkpoint input length: " + path);
  }
  std::string result(static_cast<size_t>(size), '\0');
  file.seekg(0);
  if (!file.read(result.data(), result.size())) {
    throw std::runtime_error("truncated checkpoint input: " + path);
  }
  return result;
}

// Fingerprint the executable and every loaded file-backed executable mapping,
// including Skibidy, BDM, ROOT, math and OpenMP. Installation paths participate.
inline uint64_t RuntimeSignature() {
  std::ifstream maps("/proc/self/maps");
  if (!maps) throw std::runtime_error("replay checkpoints require Linux /proc");
  std::set<std::string> paths;
  std::string line;
  while (std::getline(maps, line)) {
    std::istringstream row(line);
    std::string address, permissions, offset, device, inode, path;
    row >> address >> permissions >> offset >> device >> inode;
    std::getline(row >> std::ws, path);
    if (permissions.find('x') != std::string::npos && !path.empty() &&
        path.front() == '/') paths.insert(path);
  }
  if (paths.empty()) throw std::runtime_error("no checkpoint runtime mappings");
  uint64_t hash = kHashBasis;
  for (const auto& path : paths) {
    HashBytes(hash, path.data(), path.size());
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("cannot fingerprint runtime: " + path);
    char buffer[65536];
    while (file.read(buffer, sizeof(buffer)) || file.gcount()) {
      HashBytes(hash, buffer, file.gcount());
    }
    if (!file.eof()) throw std::runtime_error("runtime fingerprint read failed");
  }
  return hash;
}
template <typename T>
inline void HashRootObject(uint64_t& hash, const T* object) {
  TBufferFile buffer(TBuffer::kWrite);
  buffer.WriteObjectAny(object, object->IsA());
  HashBytes(hash, buffer.Buffer(), buffer.Length());
}

// Boundary witness, never a restoration payload. ROOT streamers cover private
// agent/behavior and RNG state. BDM's ParallelResizeVector ROOT streamer drops
// its data, so hash observable grid values explicitly. The inactive solver
// buffer and operation caches are reconstructed by replay, not witnessed here.
inline uint64_t StateSignature(Simulation* sim,
                               const std::vector<DerivedField*>& derived) {
  uint64_t hash = kHashBasis;
  HashObject(hash, sim->GetScheduler()->GetSimulatedSteps());
  auto* rm = sim->GetResourceManager();
  HashObject(hash, rm->GetNumAgents());
  rm->ForEachAgent([&](Agent* agent) { HashRootObject(hash, agent); });
  rm->ForEachDiffusionGrid([&](DiffusionGrid* grid) {
    HashObject(hash, grid->GetContinuumId());
    const auto& name = grid->GetContinuumName();
    HashBytes(hash, name.data(), name.size());
    const auto count = grid->GetNumBoxes();
    HashObject(hash, count);
    HashObject(hash, grid->GetLastTimestep());
    HashBytes(hash, grid->GetAllConcentrations(), count * sizeof(real_t));
    if (count) HashBytes(hash, grid->GetAllGradients(), count * 3 * sizeof(real_t));
  });
  for (auto* random : sim->GetAllRandom()) HashRootObject(hash, random);
  for (auto* field : derived) {
    HashBytes(hash, field->GetName().data(), field->GetName().size());
    HashObject(hash, field->GetNumBoxes());
    for (size_t i = 0; i < field->GetNumBoxes(); ++i) {
      HashObject(hash, field->GetConcentration(i));
    }
  }
  return hash;
}
inline std::string CanonicalConfig(toml::table config) {
  config.erase("treatment_schedule");
  if (auto* simulation = config["simulation"].as_table()) {
    simulation->erase("output_dir");
    if (simulation->empty()) config.erase("simulation");
  }
  std::ostringstream out;
  out << config;
  return out.str();
}
inline std::string PrefixSchedule(const toml::table& config, double dt,
                                  uint64_t boundary) {
  TreatmentSchedule schedule(config, dt);
  std::ostringstream out;
  for (const auto& event : schedule.Events()) {
    if (event.start_step >= boundary) break;
    out << event.start_step << '\n' << event.name.size() << ':' << event.name
        << '\n' << event.parameters << '\n';
  }
  return out.str();
}
struct Record {
  uint64_t step = 0;
  uint64_t runtime = 0;
  uint64_t state = 0;
  std::string config;
};
inline void AppendInteger(std::string& bytes, uint64_t value) {
  for (int i = 0; i < 8; ++i) bytes.push_back((value >> (i * 8)) & 255);
}
inline uint64_t ReadInteger(const std::string& bytes, size_t& cursor) {
  if (bytes.size() - cursor < 8) throw std::runtime_error("truncated checkpoint");
  uint64_t value = 0;
  for (int i = 0; i < 8; ++i) {
    value |= static_cast<uint64_t>(static_cast<unsigned char>(bytes[cursor++]))
             << (i * 8);
  }
  return value;
}
inline Record ReadCheckpoint(const std::string& directory) {
  const auto bytes = ReadFile(directory + "/checkpoint.bin", kMaxConfigBytes + 48);
  if (bytes.size() < 48 || bytes.compare(0, 8, "SKRPLY02") != 0) {
    throw std::runtime_error("unsupported or corrupt checkpoint (field-only v1 is invalid)");
  }
  size_t cursor = 8;
  Record record;
  record.step = ReadInteger(bytes, cursor);
  record.runtime = ReadInteger(bytes, cursor);
  record.state = ReadInteger(bytes, cursor);
  const auto config_size = ReadInteger(bytes, cursor);
  if (config_size > kMaxConfigBytes || bytes.size() != config_size + 48) {
    throw std::runtime_error("checkpoint length mismatch");
  }
  record.config = bytes.substr(cursor, config_size);
  cursor += config_size;
  uint64_t hash = kHashBasis;
  HashBytes(hash, bytes.data(), cursor);
  if (ReadInteger(bytes, cursor) != hash) {
    throw std::runtime_error("checkpoint integrity checksum mismatch");
  }
  return record;
}
inline void ValidateReplay(Simulation* sim, const Record& record,
                           const toml::table& current) {
  const auto saved = toml::parse(record.config);
  if (CanonicalConfig(saved) != CanonicalConfig(current)) {
    throw std::runtime_error("checkpoint configuration mismatch; change only future treatment_schedule events or simulation.output_dir");
  }
  const double dt = sim->GetParam()->simulation_time_step;
  if (PrefixSchedule(saved, dt, record.step) != PrefixSchedule(current, dt, record.step)) {
    throw std::runtime_error("checkpoint fork changes treatment history before saved boundary");
  }
  if (record.step > static_cast<uint64_t>(sim->GetParam()->Get<SimParam>()->num_steps)) {
    throw std::runtime_error("checkpoint boundary exceeds configured run length");
  }
  if (record.runtime != RuntimeSignature()) {
    throw std::runtime_error("checkpoint binary or loaded runtime mismatch; recreate checkpoint with this installation");
  }
}
inline void SaveCheckpoint(Simulation* sim, const std::string& directory,
                           const std::string& config,
                           const std::vector<DerivedField*>& derived) {
  if (config.size() > kMaxConfigBytes) throw std::runtime_error("checkpoint config too large");
  std::filesystem::create_directories(directory);
  const auto target = directory + "/checkpoint.bin";
  if (std::filesystem::exists(target)) throw std::runtime_error("checkpoint already exists: " + target);
  const auto state = StateSignature(sim, derived);
  std::string bytes("SKRPLY02", 8);
  AppendInteger(bytes, sim->GetScheduler()->GetSimulatedSteps());
  AppendInteger(bytes, RuntimeSignature());
  AppendInteger(bytes, state);
  AppendInteger(bytes, config.size());
  bytes += config;
  uint64_t hash = kHashBasis;
  HashBytes(hash, bytes.data(), bytes.size());
  AppendInteger(bytes, hash);
  const auto temporary = target + ".tmp";
  std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
  if (!file.write(bytes.data(), bytes.size())) throw std::runtime_error("checkpoint write failed: " + temporary);
  file.close();
  if (!file) throw std::runtime_error("checkpoint close failed: " + temporary);
  std::filesystem::rename(temporary, target);
  Log::Info("Checkpoint", "Saved verified replay boundary at step ",
            sim->GetScheduler()->GetSimulatedSteps(), " (", sim->GetResourceManager()->GetNumAgents(), " agents)");
}
struct CheckpointConfig {
  bool save = false;
  bool load = false;
  std::string save_dir;
  std::string load_dir;
  uint64_t save_step = 0;
};
inline CheckpointConfig GetCheckpointConfig() {
  CheckpointConfig result;
  const char* save = std::getenv("SKIBIDY_CKPT_SAVE_DIR");
  const char* load = std::getenv("SKIBIDY_CKPT_LOAD_DIR");
  const char* step = std::getenv("SKIBIDY_CKPT_STEP");
  if (save && save[0]) {
    result.save = true;
    result.save_dir = save;
    if (!step || !step[0]) throw std::runtime_error("checkpoint save requires SKIBIDY_CKPT_STEP");
    const char* end = step + std::strlen(step);
    const auto parsed = std::from_chars(step, end, result.save_step);
    if (parsed.ec != std::errc() || parsed.ptr != end) throw std::runtime_error("invalid unsigned checkpoint step");
  }
  if (load && load[0]) {
    result.load = true;
    result.load_dir = load;
  }
  if (result.save && result.load) throw std::runtime_error("save and load are mutually exclusive");
  return result;
}
inline void ValidateMode(Simulation* sim, int argc) {
  if (omp_get_max_threads() != 1 || omp_get_dynamic() || sim->GetAllRandom().size() != 1) {
    throw std::runtime_error("verified replay requires OMP_NUM_THREADS=1 and OMP_DYNAMIC=FALSE");
  }
  if (argc != 1 || sim->GetParam()->Get<SimParam>()->hot_reload ||
      !sim->GetParam()->restore_file.empty() || !sim->GetParam()->backup_file.empty()) {
    throw std::runtime_error("replay requires bdm.toml configuration, hot_reload=false and no native backup/restore");
  }
}
}  // namespace checkpoint
}  // namespace skibidy
}  // namespace bdm
#endif

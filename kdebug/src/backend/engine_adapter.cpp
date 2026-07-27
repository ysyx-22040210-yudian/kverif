#include "backend/engine_adapter.h"
#include "api/response.h"
#include "common/path_utils.h"
#include "core/process/process_runner.h"
#include "logging/action_log.h"
#include "runtime/work_dir.h"

#include <cstdlib>
#include <limits>
#include <string>

namespace kdebug {

namespace {

std::string request_session_id_for_log(const Json& request) {
    Json target = request.value("target", Json::object());
    Json args = request.value("args", Json::object());
    auto get_str = [](const Json& obj, const char* key) -> std::string {
        auto it = obj.find(key);
        return it != obj.end() && it->is_string() ? it->get<std::string>() : std::string();
    };
    std::string sid = get_str(target, "session_id");
    if (!sid.empty()) return sid;
    sid = get_str(args, "session_id");
    if (!sid.empty()) return sid;
    sid = get_str(args, "name");
    if (!sid.empty()) return sid;
    sid = get_str(target, "name");
    return sid.empty() ? "adhoc" : sid;
}

constexpr long long engine_cleanup_grace_ms(long long requested) {
    return requested / 40 < 25 ? 25 : (requested / 40 > 250 ? 250 : requested / 40);
}

static_assert(engine_cleanup_grace_ms(100) == 25, "minimum timeout cleanup grace");
static_assert(engine_cleanup_grace_ms(26000) == 250, "bounded timeout cleanup grace");

int engine_process_timeout_ms(const Json& request) {
    const Json limits = request.value("limits", Json::object());
    if (!limits.is_object()) return 0;
    const auto timeout = limits.find("timeout_ms");
    if (timeout == limits.end() ||
        !(timeout->is_number_integer() || timeout->is_number_unsigned())) {
        return 0;
    }
    long long requested = 0;
    try {
        requested = timeout->get<long long>();
    } catch (...) {
        return 0;
    }
    if (requested <= 0) return 0;
    if (requested < 100) requested = 100;

    // Leave a bounded window for the engine to terminate Verdi and serialize
    // its timeout response. Keep it below the reserve expected from an outer
    // adapter so the two process-tree deadlines cannot coincide.
    const long long cleanup_grace = engine_cleanup_grace_ms(requested);
    const long long with_cleanup_grace = requested + cleanup_grace;
    const long long maximum = std::numeric_limits<int>::max();
    return static_cast<int>(with_cleanup_grace > maximum ? maximum : with_cleanup_grace);
}

} // namespace

EngineAdapter::EngineAdapter(const std::string& executable_dir)
    : executable_dir_(executable_dir) {}

std::string EngineAdapter::engine_path() const {
    return executable_dir_ + "/libexec/kdebug-engine";
}

std::string EngineAdapter::engine_workdir() const {
    return runtime_work_dir("engine");
}

bool EngineAdapter::invoke(const Json& kdebug_request,
                           Json& response,
                           std::string& error) const {
    const std::string component = "engine";
    const std::string log_sid = request_session_id_for_log(kdebug_request);
    const std::string normalized_home = kdebug_core::kdebug_home_dir();
    if (setenv("KDEBUG_HOME", normalized_home.c_str(), 1) != 0) {
        error = "failed to propagate normalized KDEBUG_HOME to the internal engine";
        kdebug_core::log_lifecycle_event(component, log_sid, "engine.environment_failed", false,
                                         {{"kdebug_home", normalized_home}});
        return false;
    }
    const std::string path = engine_path();
    const std::string workdir = engine_workdir();

    if (!ensure_runtime_work_dir(workdir)) {
        error = std::string("failed to create engine working directory: ") + workdir;
        kdebug_core::log_lifecycle_event(component, log_sid, "engine.workdir_failed", false,
                                         {{"workdir", workdir}, {"engine_path", path}});
        return false;
    }

    // The unified engine accepts the full public request (daidir, fsdb, all fields).
    // No field stripping needed.
    std::string stdin_text = kdebug_request.dump();
    stdin_text.push_back('\n');

    ProcessRequest process_req;
    process_req.executable = path;
    process_req.argv = {"ai", "query", "-"};
    process_req.stdin_text = stdin_text;
    process_req.working_dir = workdir;
    process_req.timeout_ms = engine_process_timeout_ms(kdebug_request);

    kdebug_core::log_lifecycle_event(component, log_sid, "engine.spawning", true,
                                     {{"engine_path", path}, {"workdir", workdir},
                                      {"action", kdebug_request.value("action", std::string())}});

    ProcessRunner runner;
    ProcessResult result = runner.run(process_req);

    if (result.timed_out) {
        error = "internal engine timed out";
        if (!result.stderr_text.empty()) error += ": " + result.stderr_text;
        kdebug_core::log_lifecycle_event(component, log_sid, "engine.process_timeout", false,
                                         {{"timeout_ms", process_req.timeout_ms},
                                          {"message", error}, {"engine_path", path}});
        return false;
    }

    if (result.exit_code != 0 && !result.stderr_text.empty()) {
        error = result.stderr_text;
        kdebug_core::log_lifecycle_event(component, log_sid, "engine.process_failed", false,
                                         {{"exit_code", result.exit_code}, {"message", error},
                                          {"engine_path", path}});
        return false;
    }

    try {
        response = normalize_engine_response(Json::parse(result.stdout_text));
    } catch (const std::exception& e) {
        error = std::string("invalid internal engine response: ") + e.what() +
                " (exit=" + std::to_string(result.exit_code) + ")";
        Json ctx = {{"message", error}, {"output", result.stdout_text},
                    {"action", kdebug_request.value("action", std::string())},
                    {"exit_status", result.exit_code}};
        kdebug_core::log_lifecycle_event(component, log_sid, "engine.response_parse_failed", false, ctx);
        return false;
    }

    Json ctx = {{"action", kdebug_request.value("action", std::string())},
                {"ok", response.value("ok", false)},
                {"exit_status", result.exit_code}};
    kdebug_core::log_lifecycle_event(component, log_sid, "engine.completed",
                                     response.value("ok", true), ctx);
    return true;
}

} // namespace kdebug

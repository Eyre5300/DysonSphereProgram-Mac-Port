"""Evidence attribution only; no game behavior or device mutations."""
WORLD_PHASES = frozenset(("new_game_running", "render_regression", "shadow_regression",
    "touch_combined_regression", "interface_batch", "keyboard_regression_batch", "mouse_regression_batch",
    "save_reload_batch", "matched_large_save_render_batch", "batch_finished_normal_exit",
    "ready_for_human_test_no_auto_exit"))
class ReportIdentity:
    def __init__(self, batch_id, version, baseline):
        self.batch_id, self.version, self.baseline = batch_id, str(version), baseline
        self.legacy_boot_seen = False
    def accept(self, report):
        if not isinstance(report, dict) or not report.get("autoTestRequested"):
            return False
        if "batchIdentifier" in report or "buildVersion" in report:
            return report.get("batchIdentifier") == self.batch_id and str(report.get("buildVersion")) == self.version
        # Builds <=24 lack embedded identity. Require a changed boot report
        # AFTER native UUID verification, never infer freshness from an old world.
        if report == self.baseline:
            return False
        if report.get("phase") == "boot":
            self.legacy_boot_seen = True
        return self.legacy_boot_seen
    @staticmethod
    def entered_world(report):
        phase = report.get("phase") or ""
        return report.get("tick", 0) > 120 and (phase in WORLD_PHASES or phase.startswith("functional_batch_"))

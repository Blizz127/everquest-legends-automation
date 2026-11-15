"""Atomic, private last-observation reports; no game input or raw log text."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


class CampProgressStatus:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.error = None

    def _replace(self, name, content):
        fd, temporary = tempfile.mkstemp(prefix='.'+name+'-', dir=self.directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(content)
            os.replace(temporary, self.directory/name)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def write(self, snapshot):
        if self.error is not None:
            return False
        record=dict(snapshot,recorded_at=datetime.now(timezone.utc).isoformat(),
                    process_id=os.getpid(),current_process_verified=False)
        destination=record['arrival_destination']
        camp='unknown (stationary start)' if destination is None else destination['name']+' (at camp start)'
        level=record['client_reported_level']
        rate=record['logged_award_percent_per_hour']
        text=(f"# Last camp observation\n\nRecorded: {record['recorded_at']}\n\n"
              f"State at report: {record['state']}; this file does not prove the process is still running.\n\n"
              f"- Client-reported level: {level if level is not None else 'unknown'}\n"
              f"- Configured starting level: {record['configured_level']} (owner setting)\n"
              f"- Camp: {camp}\n"
              f"- Observation: {record['observation_seconds']:.1f} seconds\n"
              f"- Matching kills: {record['matching_kills']}\n"
              f"- Deaths observed in this session: {record['observed_deaths']}\n"
              f"- XP award messages: {record['xp_award_events']}\n"
              f"- Logged gross award rate: {f'{rate:.3f} percentage points/hour' if rate is not None else 'unavailable'}\n"
              f"- Total XP / net XP / XP units per hour: unknown\n"
              f"- Report reason: {record['finish_reason'] or record['unavailable_reason'] or 'observing'}\n\n"
              "The rate uses received client award messages. It does not establish normal/AA allocation, "
              "current position, camp suitability, or a completed leveling run.\n")
        try:
            if self.directory.is_symlink():
                raise OSError('Progress directory must be a direct directory')
            self.directory.mkdir(parents=True, exist_ok=True)
            self._replace('camp-progress.json',json.dumps(record,indent=2,sort_keys=True)+'\n')
            self._replace('STATUS.md',text)
            return True
        except OSError as error:
            self.error = str(error)
            return False  # Diagnostic storage failure cannot arm or stop a camp.

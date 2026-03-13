#!/usr/bin/python3

import os
import sys
import time
import datetime
import fileinput
import filecmp
import configparser
import glob

TIMESTAMPS = "/var/log/mythicos-mintsystem.timestamps"


class MythicOSSystem:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.logfile = open("/var/log/mythicos-mintsystem.log", "w")
        self.time_log("mythicos system started")
        self.executed = []
        self.overwritten = []
        self.skipped = []
        self.edited = []
        self.original_timestamps = {}
        self.timestamps = {}
        self.timestamps_changed = False
        self.read_timestamps()

    def time_log(self, string):
        self.log("%s - %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), string))

    def log(self, string):
        self.logfile.writelines("%s\n" % string)

    def quit(self):
        stop_time = datetime.datetime.now()
        self.log("Execution time: %s" % (stop_time - self.start_time))
        self.logfile.flush()
        self.logfile.close()
        sys.exit(0)

    def read_timestamps(self):
        if os.path.exists(TIMESTAMPS):
            with open(TIMESTAMPS) as f:
                for line in f:
                    line = line.strip()
                    items = line.split()
                    if len(items) == 2:
                        self.original_timestamps[items[0]] = items[1]
                        self.timestamps[items[0]] = items[1]

    def write_timestamps(self):
        with open(TIMESTAMPS, "w") as f:
            for filename in sorted(self.timestamps.keys()):
                f.write("%s %s\n" % (filename, self.timestamps[filename]))

    def has_changed(self, filename, collection, description):
        if not os.path.exists(filename):
            return False
        timestamp = os.stat(filename).st_mtime
        has_changed = (filename not in self.original_timestamps or
                       self.original_timestamps[filename] != str(timestamp))
        if has_changed:
            collection.append("%s (%s)" % (filename, description))
        else:
            self.skipped.append("%s (%s)" % (filename, description))
        return has_changed

    def update_timestamp(self, filename):
        self.timestamps[filename] = os.stat(filename).st_mtime
        self.timestamps_changed = True

    def replace_file(self, source, destination):
        if os.path.exists(source) and os.path.exists(destination):
            if destination not in self.overwritten and destination not in self.skipped:
                if filecmp.cmp(source, destination):
                    self.skipped.append(destination)
                else:
                    self.overwritten.append(destination)
                    os.system(f"cp {source} {destination}")

    def adjust(self):
        try:
            # Lecture configuration
            try:
                config = configparser.RawConfigParser()
                config.read('/etc/mythicos/mythicos-system.conf')
                self.enabled = (config.get('global', 'enabled') == "True")
            except:
                config = configparser.RawConfigParser()
                config.add_section('global')
                config.set('global', 'enabled', 'True')
                config.add_section('restore')
                with open('/etc/mythicos/mythicos-system.conf', 'w') as configfile:
                    config.write(configfile)
                self.enabled = True

            if not self.enabled:
                self.log("Disabled - Exited")
                self.quit()

            adjustment_dir = "/usr/share/mythicos/adjustments/"

            # Execute .execute files
            for filename in os.listdir(adjustment_dir):
                if filename.endswith(".execute"):
                    path = os.path.join(adjustment_dir, filename)
                    os.system(path)
                    self.executed.append(path)

            # Read .preserve files
            array_preserves = []
            for filename in os.listdir(adjustment_dir):
                if filename.endswith(".preserve"):
                    with open(os.path.join(adjustment_dir, filename)) as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                array_preserves.append(line)

            # Handle .overwrite files
            overwrites = {}
            for filename in os.listdir(adjustment_dir):
                if filename.endswith(".overwrite"):
                    with open(os.path.join(adjustment_dir, filename)) as f:
                        for line in f:
                            items = line.strip().split()
                            if len(items) == 2:
                                src, dst = items
                                if dst not in array_preserves:
                                    overwrites[dst] = src

            for dst, src in overwrites.items():
                if os.path.exists(src):
                    if "*" not in dst:
                        self.replace_file(src, dst)
                    else:
                        for match in glob.glob(dst):
                            self.replace_file(src, match)

            # Menu adjustments
            for filename in os.listdir(adjustment_dir):
                if filename.endswith(".menu"):
                    with open(os.path.join(adjustment_dir, filename)) as f:
                        for line in f:
                            line = line.strip()
                            items = line.split()
                            if not items:
                                continue
                            action = items[0]
                            if action == "hide" and len(items) == 2:
                                desktop_file = items[1]
                                if self.has_changed(desktop_file, self.edited, "hide"):
                                    os.system(f"grep -q -F 'NoDisplay=true' {desktop_file} || echo '\nNoDisplay=true' >> {desktop_file}")
                                    self.update_timestamp(desktop_file)
                            elif action == "show" and len(items) == 2:
                                desktop_file = items[1]
                                if self.has_changed(desktop_file, self.edited, "show"):
                                    os.system(f"sed -i -e '/^NoDisplay/d' \"{desktop_file}\"")
                                    self.update_timestamp(desktop_file)
            # Logs
            self.log("Executed: %s" % self.executed)
            self.log("Replaced: %s" % self.overwritten)
            self.log("Edited: %s" % self.edited)
            self.log("Skipped: %s" % self.skipped)
            if self.timestamps_changed:
                self.write_timestamps()
        except Exception as e:
            print(e)
            self.log(e)


if __name__ == "__main__":
    system = MythicOSSystem()
    system.adjust()
    system.quit()
    
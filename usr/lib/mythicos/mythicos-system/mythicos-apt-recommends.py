#!/usr/bin/python3

import apt
import sys
import subprocess

class RecommendsFinder:

    def __init__(self, cache, package):
        self.cache = cache
        self.package = package
        self.missing_recommends = []

        # Vérifie les paquets manquants via aptitude
        output = subprocess.getoutput(
            "/usr/local/bin/aptitude search '?broken-reverse-recommends(?installed)' | awk {'print $2;'}"
        )
        for line in output.split("\n"):
            line = line.strip()
            if line:
                self.missing_recommends.append(line)

        self.found_missing_recommends = []
        self.already_looked_at = []

        self.get_recommends(self.package, 1)

    def get_recommends(self, package, level):
        if package.name not in self.already_looked_at:
            self.already_looked_at.append(package.name)

            # Choix de la version à analyser
            if package.is_installed:
                pkg = package.installed
            else:
                pkg = package.candidate

            # Parcours des recommandations
            for recommend in pkg.recommends:
                for base_rec in recommend.or_dependencies:
                    if (
                        base_rec.name in self.missing_recommends
                        and base_rec.name not in self.found_missing_recommends
                    ):
                        self.found_missing_recommends.append(base_rec.name)
                        if base_rec.name in self.cache:
                            rec_pkg = self.cache[base_rec.name]
                            self.get_recommends(rec_pkg, level + 1)

            # Parcours des dépendances
            for dep in pkg.dependencies:
                for base_dep in dep.or_dependencies:
                    dep_name = base_dep.name
                    if dep_name in self.cache:
                        dep_pkg = self.cache[dep_name]
                        if package.is_installed and not dep_pkg.is_installed:
                            continue
                        if not package.is_installed and len(dep.or_dependencies) > 1:
                            continue
                        self.get_recommends(dep_pkg, level + 1)


if __name__ == "__main__":
    if len(sys.argv) == 2:
        package_name = sys.argv[1]
        cache = apt.Cache()
        if package_name in cache:
            package = cache[package_name]
            finder = RecommendsFinder(cache, package)
            missing_recommends = sorted(finder.found_missing_recommends)
            print("")
            if missing_recommends:
                print(f"The following missing recommended packages were found for {package_name}:\n")
                for missing in missing_recommends:
                    print(f"    {missing}")
                print("")
                print("You can install them by typing the following command:\n")
                print(f"    /usr/local/bin/apt install --install-recommends {' '.join(missing_recommends)}")
            else:
                print(f"No missing recommended packages were found for {package_name}")
            print("")
        else:
            print(f"Error: package {package_name} not found in APT cache!")
            sys.exit(1)
    else:
        print("Usage: /usr/local/bin/apt recommends [package]")
        sys.exit(1)
#!/usr/bin/python3

import apt
import sys
import subprocess
import os

if __name__ == "__main__":
    if len(sys.argv) == 2:
        package_name = sys.argv[1]
        cache = apt.Cache()

        # Mettre à jour le cache via le wrapper MythicOS
        subprocess.call(["/usr/local/bin/apt", "update"])
        print("")

        if package_name not in cache:
            print("Error: package %s not found in APT cache!" % package_name)
            sys.exit(1)

        package = cache[package_name]
        if package.is_installed:
            os.system("/usr/bin/apt download %s" % package.name)
            print("")
            print("The package %s is already installed. Its deb file was downloaded in the current directory." % package.name)
        else:
            # Création d'un dossier pour le package
            subprocess.call(["mkdir", "-p", package.name])
            os.chdir(package.name)
            os.system("rm -rf *.deb")

            # Télécharger toutes les dépendances nécessaires pour une installation hors-ligne
            os.system(
                "LC_ALL=C /usr/local/bin/apt install --dry-run %s | grep ^Inst | awk {'print $2;'} | xargs /usr/local/bin/apt download" % package.name
            )

            # Ajouter le script d'installation de MythicOS
            os.system("cp /usr/lib/mythicos/mythicos-system/apt/install ./")
            os.system("chmod a+rx ./install")
            os.chdir("..")

            # Création de l'archive tar.gz
            os.system("tar cvf %s.tar %s/ >/dev/null" % (package.name, package.name))
            os.system("gzip %s.tar" % package.name)
            os.system("rm -rf '%s'" % package.name)
            print("")
            print(
                "The packages were downloaded into %s.tar.gz. This archive contains all the packages necessary for an offline installation." % package.name
            )

    else:
        print("Usage: apt download [package]")
        sys.exit(1)
        
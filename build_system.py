import yaml
import os
from subprocess import run
import subprocess
import re

"""
Takes a barebones @base Gentoo and configures it into a usable system

- TODO
    - Docker Containers and images are lost
        - Data is still on home though.
    - cron is lost
- Usage
    - First update to ensure all the kernels align to the same version
       in @base, @current and @
        - Mount, chroot and then Update:
            - @base
            - @current
        - Update vmlinuz.efi and initramfs.img in /boot/efi/{.,base}
        - Ensure @base boots
            - Snapshot @base to @base-ro
        - Move @current to @
        - Ensure @ boots
        - Make a @current, @current-ro and @base
    - Snapshot @base into @candidate
    - Chroot into @candidate
    - Run this script
    - Move @candidate to @
        - If it does not boot
            - Reboot into @base and move back to the original @
"""


with open("config.yaml") as f:
    config = yaml.load(f, Loader=yaml.FullLoader)


def main():
    i = 0

    # print(f"{(i := i + 1)} Snapshot Base into Candidate")
    # # TODO

    # chroot into the new system

    print(f"{(i := i + 1)} Creating User")
    create_user()

    print(f"{(i := i + 1)} Creating podman groups")
    create_podman_groups()

    print(f"{(i := i + 1)} Set Use Flags")
    set_use_flags()

    print(f"{(i := i + 1)} Updating System")
    run(emerge() + ["--sync"])
    run(emerge() + ["uND", "@world"])

    # print(f"{(i := i + 1)} Install torbrowser")
    install_torbrowser()

    if config["nvidia"]:
        print(f"{(i := i + 1)} Configuring Nvidia")
        configure_nvidia()
    else:
        print(f"{(i := i + 1)} Nvidia is False... Skipping")

    print(f"{(i := i + 1)} Set Profile")
    run(["eselect", "profile", "set", config["profile"]])
    run(emerge() + ["-uND", "@world"])

    print(f"{(i := i + 1)} Install Packages")
    install(config["packages"])

    print(f"{(i := i + 1)} Enable NTP and IWD")
    enable("iwd")
    enable("ntpd")

    print(f"{(i := i + 1)} Set Display Manager")
    set_display_manager()

    print(f"{(i := i + 1)} Add user to Podman Group")
    configure_docker()

    # print(f"{(i := i + 1)} Snapshot Candidate into BASE")
    # # TODO


def create_user():
    if not os.path.exists(config["shell"]):
        print(f"Shell ({config['shell']})  not installed, using /bin/bash")
        config_shell = "/bin/bash"
    run(["useradd", "-m", "-G", "users,wheel,audio,video,cron", "-s", config["shell"]])
    run(["su", config["user"], "-c", "xdg-user-dirs-update"])
    run(["su", config["user"], "-c", f"mkdir -p /home/{config['user']}/.local/share"])


def enable(service: str, level: str = "default"):
    run(["rc-update", "add", service, level])


def create_podman_groups():
    for u in ["u", "g"]:
        run(["usermod", f"--add-sub{u}ids", "1001000000-1001999999", config["user"]])


def emerge():
    """
    Returns a list of emerge with options from config
    """
    return ["emerge", "--verbose", f"--getbinpkg={config['binaries']}"]


def install(pkg: list[str]):
    # remove empty packages
    pkg = [p for p in pkg if p]
    run(emerge() + pkg)


def touch(file: str):
    with open(file, "w") as f:
        f.write("")


def set_use_package_accept(package: str, flag: str = "~*", filename: str | None = None):
    if not filename:
        filename = package.split("/")[1]
    line = f"{package} {flag}\n"

    # Don't write duplicate lines
    if os.path.exists(filename):
        with open(f"/etc/portage/package.accept_keywords/{filename}", "r") as f:
            lines = f.read().splitlines()
            if line in lines:
                return

    with open(f"/etc/portage/package.accept_keywords/{filename}", "a") as f:
        f.write(line)


def set_use_licence(package: str, flag: str, filename: str | None = None):
    if not filename:
        filename = package.split("/")[1]
    licence_dir = "/etc/portage/package.license"  # verb with s
    warning = f"""
    {licence_dir} must be a directory, fix:

    mv {licence_dir} /tmp
    mkdir {licence_dir}/
    mv /tmp/{os.path.basename(licence_dir)} {licence_dir}/misc
    """

    assert os.path.isdir(licence_dir), warning

    with open(f"{licence_dir}/{filename}", "a") as f:
        f.write(f"{package} {flag}\n")


def set_use_flag(package: str, flag: str, filename: str | None = None):
    if not filename:
        filename = package.split("/")[1]
    with open(f"/etc/portage/package.use/{filename}", "a") as f:
        f.write(f"{package} {flag}\n")


def set_use_flags():
    for k, v in {
        "net-firewall/iptables": "nftables",
        "gnome-base/nautilus-previewer": "-previewer",
        "net-vpn/i2pd": "upnp",
    }.items():
        set_use_flag(k, v)

    with open("/etc/portage/make.conf", "a") as f:
        f.write('''USE="${USE} -gnome-online-accounts"''' + "\n")

    for k, v in {
        "app-portage/emlop": "**",
        "dev-util/rustup": "~*",
        "x11-terms/wezterm": "~*",
    }.items():
        set_use_package_accept(k, v)


def install_torbrowser():
    pkg_repo = "torbrowser"
    pkg_name = "torbrowser-launcher"
    pkg_dir = "www-client"
    pkg = f"{pkg_dir}/{pkg_name}"

    install(["eix", "app-eselect/eselect-repository"])
    run(["eselect", "repository", "enable", pkg_repo])
    run(["emerge", "--sync", pkg_repo])
    run(["eix-remote", "update"])
    run(["eix-sync"])
    set_use_package_accept(pkg, "~*")
    set_use_flag("app-crypt/gpgme", "python", pkg_name)
    install(pkg)


def enable_guru():
    run(["eselect", "repository", "enable", "guru"])
    # run(["emerge", "--sync", "guru"])
    run(["emaint", "--auto", "sync"])


def configure_nvidia():
    # Installable Packages: License and Accept keywords
    nvidia_packages = {
        "dev-util/nvidia-cuda-toolkit": ["~*", "NVIDIA-CUDA"],
        "sys-firmware/nvidia-firmware": ["~*", "NVIDIA-r2"],
        "x11-drivers/nvidia-drivers": ["~*", "NVIDIA-r2"],
        "app-containers/nvidia-container-toolkit": ["~*", ""],
    }
    for k, (a, li) in nvidia_packages.items():
        if a:
            set_use_package_accept(k, a, filename="nvidia")
        if li:
            set_use_licence(k, li, filename="nvidia")

    # Only Flags
    set_use_package_accept("sys-libs/libnvidia-container", "~*", filename="nvidia")
    set_use_flag("x11-libs/cairo", flag="X", filename="nvidia")

    # Install the Packages
    enable_guru()
    install(list(nvidia_packages.keys()))


def set_display_manager():
    dm_conf = "/etc/conf.d/display-manager"
    dm = config["dm"]

    # Modify the lines in the file
    if os.path.exists(dm_conf):
        run(["cp", dm_conf, f"{dm_conf}.bak"])
        # Replace the current display manager with gdm
        with open(dm_conf, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if "DISPLAYMANAGER=" in line:
                lines[i] = f'DISPLAYMANAGER="{dm}"'
    else:
        lines = ['DISPLAYMANAGER="gdm"']

    # Write the lines to the config
    with open(dm_conf, "w") as f:
        f.writelines(lines)

    enable("elogind", "boot")
    enable("display-manager", "default")


def configure_docker():
    run(["usermod", "-aG", "docker", config["user"]])
    enable("docker", "default")

    # Mount Home and start any needed containers (so they're there next boot)
    run(["mount", "LABEL=Butter", "-o", "subvol=@home", "/home"])

    home = f"/home/{config['user']}"
    for c in config['containers']:
        try:
            run(
                ["docker", "compose", "f", f"{home}/{c}/docker-compose.yml", "up", "-d"]
            )
        except Exception:
            pass


def get_installed_packages() -> list[str]:
    with open("/var/lib/portage/world", "r") as f:
        installed_packages = f.read().splitlines()
        return [p for p in installed_packages if p]


if __name__ == "__main__":
    main()

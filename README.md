# Gentoo Install Scripts

## Introduction

This repository contains scripts to install Gentoo Linux on a computer. The scripts are designed to create a reproducible system that is semi-immutable.

## Motivation

I was inspired by immutable OS like Silverblue, NixOS and OpenSuse Aeon. However, I didn't like the complexity of those systems and wanted to create a similar system with Gentoo.

The idea is to use subvolumes and update in those subvolumes via chroot before migrating that snapshot over `@`.

This fixes the pain points of Gentoo, mostly updates not building packages that work on a fresh system but not the current one because of gremlens.


## Workflow

### Overview

The basic idea is:

  - ro
      - `@base` --
          - This is the result of oddlama's `gentoo-install` script.
              - It includes basic packages like vim, git, iwd etc.
              - This is documented in [./oddlamma-install-gentoo.org](./oddlamma-install-gentoo.org)
      - `@current` -- unused
          - This is the result of the `./build_system.py` script.
              - This includes the latest packages and configurations.
          - This subvolume is not used
  -rw
      - `@`
          - This is the live system and is a snapshot of `@current`.
      - `@candidate`
          - This is a snapshot of `@base` that is built with the `./build_system.py` script before moving to `@`.



I wanted to create a system that is reproducible and semi-immutable. I wanted to create a system that is easy to maintain and upgrade.

### Installing Packages

1. Docker and Podman Containers
2. Distrobox
3. Flatpak
4. Chroot into a subvolume with Bubblewrap
5. pipx, cargo, npm, gem, etc.
6. emerge
    - These should be added to ./build_system.py

### Updating

Updates should happen on a subvolume that is not used and then be moved to `@`. This way any divergence in `@` is clobbered by the new snapshot.

#### Minor

##### Overview

Update the `@current` snapshot and move it over the top of `@`.

##### Procedure

1. Update the main system, including kernels and packages.
    - Copy the kernels to `/boot/efi` and and update the initramfs with `dracut`
    - This is easier as it ensures the kernels all match before rebooting.
2. Reboot and ensure all is well
    - If there is an issue, boot into `@base` and fix the issue.
3. Chroot into `@current` and update as above
4. Snapshot `@current` to `@candidate` and ensure it boots
5. Snapshot `@candidate` to `@` and reboot

#### Major

##### Overview

Update the `@base` snapshot, build it with `./build_system.py` and move it over the top of `@`.

##### Procedure

1. Update the main system, including kernels and packages.
    - Copy the kernels to `/boot/efi` and and update the initramfs with `dracut`
    - This is easier as it ensures the kernels all match before rebooting.
2. Reboot and ensure all is well
    - If there is an issue, boot into `@base` and fix the issue.
3. Chroot into `@base` and update as above
4. Snapshot `@base` to `@candidate`
5. chroot into `@candidate` and run `./build_system.py`
6. Boot of `@candidate` and ensure all is well
7. NOTE: At this stage take note of the following which may be lost (These should be added to `./build_system.py`):
    - Docker Images
        - Running Docker containers with `restart: unless-stopped`
    - crontab
    - Additional Running Services
5. Snapshot `@candidate` to `@` and reboot






# gentoo-install-scripts

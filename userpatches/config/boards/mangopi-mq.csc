# Mangue OS additions to upstream config/boards/mangopi-mq.csc (sourced after it).
# Adds the mainline "current" branch (6.18 LTS) alongside upstream's smaeul "edge".
KERNEL_TARGET="edge,current"
declare -g KERNEL_BTF="no" # no DWARF/BTF: 400 MB image deb otherwise

# Serial line noise (adapter TX on pin 10) halted autoboot on 2026-10-10.
# Only the string "mq" stops autoboot now.
function post_config_uboot_target__mangue_keyed_autoboot() {
	display_alert "Mangue OS" "U-Boot keyed autoboot (stop string 'mq')" "info"
	run_host_command_logged scripts/config --enable CONFIG_AUTOBOOT_KEYED
	run_host_command_logged scripts/config --set-str CONFIG_AUTOBOOT_PROMPT "'Autoboot in %d s - type mq to stop\\n'"
	run_host_command_logged scripts/config --set-str CONFIG_AUTOBOOT_STOP_STR "mq"
	run_host_command_logged scripts/config --disable CONFIG_AUTOBOOT_ENCRYPTION
	# No persistent U-Boot env: a stray saveenv must never lock in a bad boot config.
	run_host_command_logged scripts/config --disable CONFIG_ENV_IS_IN_FAT
	run_host_command_logged scripts/config --enable CONFIG_ENV_IS_NOWHERE
	# U-Boot left the D1 watchdog running (16 s) and nothing fed it before userspace:
	# a slow first boot was reset at ~16 s on 2026-10-10. Don't autostart it.
	run_host_command_logged scripts/config --disable CONFIG_WATCHDOG_AUTOSTART
}

# Pi-style FAT /boot (user decision 2026-10-10): extlinux.conf, kernel, DTB, overlays and
# mangue-setup.txt editable from Windows. Must run after upstream's
# post_family_config__mangopi_source_boot, which forces BOOTSIZE=0 BOOTFS_TYPE="".
# Firmware still ends before sector 8160; the boot partition starts at OFFSET (4 MiB).
function post_family_config__990_mangue_fat_boot() {
	declare -g BOOTFS_TYPE="fat" BOOTSIZE=256
	display_alert "Mangue OS" "FAT /boot ${BOOTSIZE} MiB" "info"
}

# B8: clean kernel cmdline. Upstream board adds stmmaceth=chain_mode:1 (MQ Pro has no Ethernet),
# common.conf adds "splash plymouth.ignore-serial-consoles" (no plymouth) and a 2nd "rw".
# Set right before extlinux.conf is written (partitioning.sh), after all config sourcing.
function pre_prepare_partitions__990_mangue_cmdline() {
	declare -g SRC_CMDLINE="console=ttyS0,115200n8 console=tty0 earlycon=sbi rootflags=data=writeback rw rootwait"
	declare -g MAIN_CMDLINE="no_console_suspend consoleblank=0 fsck.fix=yes fsck.repair=yes net.ifnames=0"
	display_alert "Mangue OS" "cmdline: ${SRC_CMDLINE} ${MAIN_CMDLINE}" "info"
}

# Repo lockdown: Armbian re-adds armbian.sources ("image-late") after customize-image.sh,
# and a package drops armbian-config.sources. Remove both at the last repo stage.
function post_repo_customize_image__990_mangue_no_armbian_repo() {
	display_alert "Mangue OS" "removing Armbian apt sources" "info"
	rm -f "${SDCARD}"/etc/apt/sources.list.d/armbian*.sources "${SDCARD}"/etc/apt/sources.list.d/armbian*.list \
		"${SDCARD}"/etc/apt/sources.list.d/armbian*.disabled
}

# Windows only gives a drive letter to GPT partition types it knows. Armbian marks the FAT /boot as
# "Linux extended boot" (XBOOTLDR), which Windows ignores -> beginners could not see mangue-setup.txt.
# Mark it "Microsoft basic data" instead; U-Boot reads the FAT regardless and fstab mounts by UUID.
function post_create_partitions__991_mangue_boot_visible_on_windows() {
	[[ -n "${bootpart}" ]] || return 0
	run_host_command_logged sfdisk --part-type "${SDCARD}.raw" "${bootpart}" EBD0A0A2-B9E5-4433-87C0-68B6B72699C7
	display_alert "Mangue OS" "boot partition ${bootpart} type: Microsoft basic data (visible on Windows)" "info"
}

#!/bin/bash
# Benchmark suite for the MQ Pro, comparable to published Pi Zero 2 W numbers.
# Run on the board as root: sudo bash bench.sh  → results in /root/bench/
# Refs: CNX sbc-bench (7-zip, memcpy/memset, openssl), notenoughtech (7z b, iperf3).
set -u
OUT=/root/bench; mkdir -p "$OUT"; cd "$OUT"
log() { echo "=== $(date -Is) $*" | tee -a summary.txt; }
temp() { awk '{printf "%.1f C\n", $1/1000}' /sys/class/thermal/thermal_zone0/temp 2>/dev/null; }

log "start; temp $(temp)"
uname -a > sysinfo.txt; cat /proc/cpuinfo >> sysinfo.txt

log "7-zip (7z b), 3 runs"
for i in 1 2 3; do 7z b > 7zip_$i.txt 2>&1; grep -E '^Tot:' 7zip_$i.txt | tee -a summary.txt; done

log "sysbench cpu (prime 10000, 1 thread, 10 s)"
sysbench cpu --cpu-max-prime=10000 --threads=1 --time=10 run > sysbench_cpu.txt 2>&1
grep 'events per second' sysbench_cpu.txt | tee -a summary.txt

log "sysbench memory (1M blocks, 10 s)"
sysbench memory --memory-block-size=1M --memory-total-size=100G --time=10 run > sysbench_mem.txt 2>&1
grep -E 'MiB/sec' sysbench_mem.txt | tee -a summary.txt

log "openssl speed aes-256-cbc / sha256"
openssl speed -elapsed -evp aes-256-cbc > openssl_aes.txt 2>&1; tail -1 openssl_aes.txt | tee -a summary.txt
openssl speed -elapsed -evp sha256 > openssl_sha.txt 2>&1; tail -1 openssl_sha.txt | tee -a summary.txt

log "CoreMark (-O2, gcc $(gcc -dumpversion))"
[ -d coremark ] || git clone -q --depth 1 https://github.com/eembc/coremark.git
make -C coremark XCFLAGS="-O2 -DPERFORMANCE_RUN=1" REBUILD=1 > coremark_build.txt 2>&1
grep -E 'Iterations/Sec|CoreMark 1.0' coremark/run1.log | tee -a summary.txt

log "fio SD (seq 1M r/w, rand 4k r/w), 256 MB file"
for t in "read 1M" "write 1M" "randread 4k" "randwrite 4k"; do set -- $t
  fio --name=$1 --filename=/root/fio.tmp --size=256M --rw=$1 --bs=$2 --direct=1 \
      --ioengine=libaio --iodepth=4 --runtime=30 --time_based --group_reporting > fio_$1.txt 2>&1
  echo "$1 $2: $(grep -E '^\s+(READ|WRITE):' fio_$1.txt)" | tee -a summary.txt
done; rm -f /root/fio.tmp

log "stress-ng 120 s thermal; temp before $(temp)"
stress-ng --cpu 1 --cpu-method matrixprod --metrics-brief -t 120 > stress.txt 2>&1
log "temp after stress $(temp); throttling check: $(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq 2>/dev/null) kHz"
log "done"

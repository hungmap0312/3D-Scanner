#ifndef FRESH_CAPTURE_CORE_H
#define FRESH_CAPTURE_CORE_H

#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <inttypes.h>

#ifdef __cplusplus
#include <atomic>
extern "C" {
#endif

#define FRESH_CAPTURE_TIMEOUT_US       1500000LL  // 1.5 s deadline for fresh frame
#define FRESH_CAPTURE_MAX_DISCARD      5          // Stop at 5th stale frame (discard <= 4)
#define FRESH_CAPTURE_MUTEX_WAIT_MS    100        // 100 ms nominal mutex wait
#define FRESH_CAPTURE_BOOT_ID_LEN      32         // 128-bit hex string = 32 chars

typedef enum {
    FRESH_CAPTURE_OK = 0,
    FRESH_CAPTURE_ERR_BUSY_STREAM,
    FRESH_CAPTURE_ERR_BUSY_CAPTURE,
    FRESH_CAPTURE_ERR_NO_BUFFER,
    FRESH_CAPTURE_ERR_TIMEOUT_NO_FRESH_FRAME,
    FRESH_CAPTURE_ERR_UNSUPPORTED_FORMAT,
    FRESH_CAPTURE_ERR_FRAME_ID_OVERFLOW,
    FRESH_CAPTURE_ERR_INTERNAL
} fresh_capture_status_t;

static inline bool fresh_capture_is_fresh(int64_t t_frame_us, int64_t t_req_us) {
    return t_frame_us > t_req_us;
}

static inline int64_t fresh_capture_make_timestamp_us(uint32_t sec, uint32_t usec) {
    return ((int64_t)sec) * 1000000LL + (int64_t)usec;
}

static inline void fresh_capture_split_timestamp_us(int64_t ts_us, uint32_t *sec, uint32_t *usec) {
    if (ts_us < 0) {
        if (sec) *sec = 0;
        if (usec) *usec = 0;
        return;
    }
    if (sec) *sec = (uint32_t)(ts_us / 1000000LL);
    if (usec) *usec = (uint32_t)(ts_us % 1000000LL);
}

static inline int fresh_capture_format_timestamp(char *buf, size_t buf_sz, uint32_t sec, uint32_t usec) {
    return snprintf(buf, buf_sz, "%" PRIu32 ".%06" PRIu32, sec, usec);
}

static inline bool fresh_capture_allocate_id(uint64_t *counter, bool *max_served, uint64_t *out_id) {
    if (!counter || !max_served || !out_id) {
        return false;
    }
    if (*max_served) {
        return false; // Overflow: UINT64_MAX already served
    }
    if (*counter == UINT64_MAX) {
        *max_served = true;
        return false; // Cannot allocate beyond UINT64_MAX
    }
    (*counter)++;
    *out_id = *counter;
    if (*counter == UINT64_MAX) {
        *max_served = true;
    }
    return true;
}

static inline void fresh_capture_bytes_to_hex(const uint8_t *bytes, size_t len, char *hex_out) {
    static const char hex_digits[] = "0123456789abcdef";
    for (size_t i = 0; i < len; i++) {
        hex_out[i * 2]     = hex_digits[(bytes[i] >> 4) & 0x0F];
        hex_out[i * 2 + 1] = hex_digits[bytes[i] & 0x0F];
    }
    hex_out[len * 2] = '\0';
}

#ifdef __cplusplus
}
#endif

#endif // FRESH_CAPTURE_CORE_H

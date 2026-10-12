/*
 * tester_c4_simexe.c - "bo Nucleo gia" chay ping_proto.c THAT qua stdin/stdout, de
 * pc/test_nucleo_ping_p1.py noi cong cu PC (pc/nucleo_ping.py) voi ma firmware that
 * ma khong can bo (MinGW gcc 32-bit, Python 64-bit: khong nap DLL duoc nen dung tien trinh).
 *
 * Moi dong lenh tu stdin, moi dong tra loi ra stdout:
 *   R <door> <estop> <rcc_flags> <tick>  reset bo (PA8 thap, BOOT vao bo dem)   -> O <hex>
 *   I <door> <estop>                     dat chan cua/estop                      -> K
 *   T <tick>                             dat tick                                -> K
 *   X <hex>                              byte UART den, roi ping_poll()          -> O <hex byte bo gui>
 *   P                                    ping_poll()                             -> O <hex>
 *   S                                    -> S <state> <last_err> <pa8> <so vi pham PA8>
 * Build (Git Bash, tu firmware/stm32/NucleoPing):
 *   /d/MinGW/bin/gcc -std=c99 -Wall -Wextra -O0 -Itest/fake -ICore/Inc -DFW_GIT_HASH='"hosttest"' \
 *     test/tester_c4_simexe.c test/tester_c4_hal.c Core/Src/ping_proto.c -o <TMP>/tester_c4_sim.exe
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void sim_reset(int door, int estop, uint32_t rcc_flags, uint32_t tick, int pa8_before, int with_iwdg);
void sim_set_inputs(int door, int estop);
void sim_set_tick(uint32_t t);
void sim_poll(void);
void sim_rx(const char *bytes, int n);
int sim_take_tx(char *buf, int cap);
int sim_pa8(void);
uint32_t sim_pa8_violations(void);
const char *sim_state(void);
const char *sim_last_err(void);

static void out_tx(void)
{
  static char buf[32768];
  int n = sim_take_tx(buf, (int)sizeof(buf)), i;
  printf("O ");
  for (i = 0; i < n; i++) printf("%02X", (unsigned char)buf[i]);
  printf("\n");
  fflush(stdout);
}

int main(void)
{
  static char line[8192];
  static char bytes[4096];
  while (fgets(line, sizeof(line), stdin)) {
    if (line[0] == 'R') {
      int d = 1, e = 0;
      unsigned long f = 2, t = 1000;
      sscanf(line + 1, "%d %d %lu %lu", &d, &e, &f, &t);
      sim_reset(d, e, (uint32_t)f, (uint32_t)t, 0, 1);
      out_tx();
    } else if (line[0] == 'I') {
      int d = 1, e = 0;
      sscanf(line + 1, "%d %d", &d, &e);
      sim_set_inputs(d, e);
      printf("K\n");
      fflush(stdout);
    } else if (line[0] == 'T') {
      unsigned long t = 0;
      sscanf(line + 1, "%lu", &t);
      sim_set_tick((uint32_t)t);
      printf("K\n");
      fflush(stdout);
    } else if (line[0] == 'X') {
      const char *p = line + 2;
      int n = 0;
      unsigned v;
      while (p[0] && p[1] && p[0] != '\n' && p[0] != '\r' && n < (int)sizeof(bytes) && sscanf(p, "%2x", &v) == 1) {
        bytes[n++] = (char)v;
        p += 2;
      }
      sim_rx(bytes, n);
      sim_poll();
      out_tx();
    } else if (line[0] == 'P') {
      sim_poll();
      out_tx();
    } else if (line[0] == 'S') {
      printf("S %s %s %d %lu\n", sim_state(), sim_last_err(), sim_pa8(), (unsigned long)sim_pa8_violations());
      fflush(stdout);
    }
  }
  return 0;
}

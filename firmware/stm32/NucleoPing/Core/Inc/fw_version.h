/*
 * Phien ban firmware NucleoPing.
 *
 * FW_VERSION: tang tay khi doi giao thuc hoac hanh vi.
 * FW_GIT_HASH: Makefile truyen vao tu `git describe --always --dirty`;
 * neu build ngoai Git thi la "nogit". Chuoi nay xuat hien trong dong BOOT
 * va tra loi ID? de hoi so phien quet voi commit ma nguon.
 */
#ifndef FW_VERSION_H
#define FW_VERSION_H

#define FW_VERSION "0.2.0"

#ifndef FW_GIT_HASH
#define FW_GIT_HASH "nogit"
#endif

#endif /* FW_VERSION_H */

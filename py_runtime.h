#ifndef PY_RUNTIME_H
#define PY_RUNTIME_H

#ifdef __cplusplus
extern "C" {
#endif

void py_print_int(int value);
void py_print_float(double value);
void py_print_str(const char *value);

#ifdef __cplusplus
}
#endif

#endif

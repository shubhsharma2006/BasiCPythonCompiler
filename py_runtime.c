#include "py_runtime.h"

#include <stdio.h>

void py_print_int(int value) {
    printf("%d\n", value);
}

void py_print_float(double value) {
    printf("%g\n", value);
}

void py_print_str(const char *value) {
    printf("%s\n", value ? value : "");
}

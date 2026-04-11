#include "py_runtime.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void py_print_int(int value) {
    printf("%d\n", value);
}

void py_print_float(double value) {
    printf("%g\n", value);
}

void py_print_str(const char *value) {
    printf("%s\n", value ? value : "");
}

void py_print_bool(int value) {
    printf("%s\n", value ? "True" : "False");
}

void py_write_int(int value) {
    printf("%d", value);
}

void py_write_float(double value) {
    printf("%g", value);
}

void py_write_str(const char *value) {
    printf("%s", value ? value : "");
}

void py_write_bool(int value) {
    printf("%s", value ? "True" : "False");
}

const char *py_int_to_str(int value) {
    char *buf = (char *)malloc(32);
    snprintf(buf, 32, "%d", value);
    return buf;
}

const char *py_float_to_str(double value) {
    char *buf = (char *)malloc(64);
    snprintf(buf, 64, "%g", value);
    return buf;
}

const char *py_bool_to_str(int value) {
    return value ? "True" : "False";
}

const char *py_str_identity(const char *value) {
    return value ? value : "";
}

const char *py_str_concat(const char *a, const char *b) {
    const char *sa = a ? a : "";
    const char *sb = b ? b : "";
    size_t la = strlen(sa);
    size_t lb = strlen(sb);
    char *result = (char *)malloc(la + lb + 1);
    memcpy(result, sa, la);
    memcpy(result + la, sb, lb + 1);
    return result;
}

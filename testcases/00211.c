#ifdef __cplusplus
extern "C" {
#endif
extern int printf(const char *format, ...);
#ifdef __cplusplus
}
#endif

#define ACPI_TYPE_INVALID       0x1E
#define NUM_NS_TYPES            ACPI_TYPE_INVALID+1
int array[NUM_NS_TYPES];

#define n 0xe
int main()
{
    printf("n+1 = %d\n", n+1);
//    printf("n+1 = %d\n", 0xe+1);
}

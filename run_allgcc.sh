#!/bin/sh

declare -A GCC_DICT

C17_FLAG="c17"
C11_FLAG="c11"
C99_FLAG="c99"
C90_FLAG="c90"
GNU90_FLAG="gnu90"
C89_FLAG="c89"
GNU89_FLAG="gnu89"
GNU9X_FLAG="gnu9x"

GCC_DICT=(
  ["9.3.0"]="$C17_FLAG $C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["8.4.0"]="$C17_FLAG $C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["7.5.0"]="$C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["6.5.0"]="$C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["5.5.0"]="$C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["4.9.4"]="$C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["4.8.5"]="$C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["4.7.4"]="$C11_FLAG $C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["4.6.4"]="$C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["4.5.4"]="$C99_FLAG $C90_FLAG $GNU90_FLAG"
  ["4.4.7"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["4.3.6"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["4.2.4"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["4.1.2"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["4.0.4"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["3.4.6"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["3.3.6"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["3.2.3"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["3.1.1"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["3.0.4"]="$C99_FLAG $C89_FLAG $GNU89_FLAG"
  ["2.95.3"]="$GNU9X_FLAG $C89_FLAG $GNU89_FLAG"
)


OLDGCC_LIST=(
  "2.91.66" "2.8.1" "2.7.2" "2.6.3" "2.5.8" "2.4.5" "2.3.3" "2.2.2" "2.1" "2.0"
)

for gcc in ${!GCC_DICT[@]}
do
  cflags=${GCC_DICT[$gcc]}
  for cflag in ${cflags[@]}
  do
    echo CC="gcc-$gcc" CFLAGS="-std=$cflag -O2" ./runtests.sh
    CC="gcc-$gcc" CFLAGS="-std=$cflag -O2" ./runtests.sh > results/gcc-$gcc-$cflag.txt
  done
done

for gcc in ${OLDGCC_LIST[@]}
do
  echo CC="gcc-$gcc" CFLAGS="-O2" ./runtests.sh ./runtests.sh
  CC="gcc-$gcc" CFLAGS="-O2" ./runtests.sh ./runtests.sh > results/gcc-$gcc.txt
done

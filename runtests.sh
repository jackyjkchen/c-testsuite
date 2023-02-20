#/bin/sh

CC=${CC:-gcc}
CFLAGS=${CFLAGS:--std=c11 -O2}

TOTAL=0
PASS=0
FAIL=0
FAIL_CASES=()

execute_tests() {
  echo CC=${CC}
  echo CFLAGS=${CFLAGS}
  pushd ./testcases >/dev/null || exit 1
  for testcase in *.c
  do
    if run_test ${testcase}
    then
      PASS=$((${PASS}+1))
    else
      FAIL=$((${FAIL}+1))
      FAIL_CASES+=( ${testcase} )
    fi
    TOTAL=$((${TOTAL}+1))
  done
  popd >/dev/null
}

run_test() {
  local case=${1}
  if ! $CC $CFLAGS ${case} -o ${case}.bin >${case}.ccout 2>${case}.ccerr
  then
    return -1
  fi
  if ! ./${case}.bin > ${case}.output 2>&1
  then
    return -1
  fi
  if ! diff -u ${case}.expected ${case}.output
  then
    return -1
  fi
  return 0
}

execute_tests


echo Summary
echo Total:
echo ${TOTAL}
echo Pass:
echo ${PASS}
echo Fail:
echo ${FAIL}
echo Failed Cases:
echo ${FAIL_CASES[@]}

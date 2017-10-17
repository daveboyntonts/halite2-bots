#!/bin/bash

if [ -n "$1" ]; then
	seed="-s $1"
fi
rm -f *.log

python -m py_compile MyBot.py || exit 1
./halite.exe ${seed} -t -d "240 160" "python MyBot_0.9.5.py" "python MyBot.py" | egrep -v "^Turn"


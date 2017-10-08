#!/bin/bash

if [ -n "$1" ]; then
	seed="-s $1"
fi
rm -f *.log
python -m py_compile MyBot.py || exit 1
./halite.exe ${seed} -d "336 224" "python MyBot_0.9.1.py" "python MyBot.py" \
	"python MyBot_0.9.4.py" "python MyBot_0.9.3.py" | egrep -v "^Turn"

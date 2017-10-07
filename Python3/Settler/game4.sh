#!/bin/bash

rm -f *.log
python -m py_compile MyBot.py || exit 1
./halite.exe -d "280 260" "python MyBot_0.9.1.py" "python MyBot.py" \
	"python MyBot_0.9.py" "python MyBot_0.7.py" | egrep -v "^Turn"

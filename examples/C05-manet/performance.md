# Performance

## PC Environment
- VM : Parallels
- OS : ubuntu20.04
- Processors : 4
- Memory: 16GB

# Node Environment
- Node Total : 50 

## Move And Calc
- C++
    - with Thread: 37 miliseconds
    - without Thread: 0.614 miliseconds

- Python (numpy)
    - without Thread: 20 miliseconds

## TC
- C++ (50*49)/2
    - with Thread: 43606 miliseconds (not consistent)
    - without Thread: 113195 miliseconds

- Python
    - with Thread: 25000 miliseconds

    - investigate what takes times with python
#!/bin/bash

# for i in {0..7}
# 	do
# 		cd A0$i*
# 		rm -rf output
# 		./*.py
# 		cd ..
# 	done

# for i in {20..21}
# 	do
# 		cd A$i*
# 		rm -rf output
# 		./*.py
# 		cd ..
# 	done

# for i in {0..9}
# 	do
# 		cd B0$i*
# 		rm -rf output
# 		./*.py
# 		cd ..
# 	done

# for i in {0..4}
# 	do
# 		cd C0$i*
# 		rm -rf output
# 		./*.py
# 		cd ..
# 	done

#!/bin/bash

for i in {0..7}
	do
		cd A0$i*
		pwd
		ls
		cd ..
	done

for i in {20..21}
	do
		cd A$i*
		pwd
		ls
		cd ..
	done

for i in {0..9}
	do
		cd B0$i*
		pwd
		ls
		cd ..
	done

for i in {0..4}
	do
		cd C0$i*
		pwd
		ls
		cd ..
	done



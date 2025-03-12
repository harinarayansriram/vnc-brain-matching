gcc -O3 -Wall -fopenmp xoshiro.c heap.c utils.c interrupts.c parallel_hungarian.c parallel_hungarian_subset.c .\score_lookup.c -o score_lookup
cd ../create_score_lookup
gcc -O3 -Wall -fopenmp .\parallel_create_score_lookup.c -o parallel_create_score_lookup
./parallel_create_score_lookup.exe ../gm.csv ../gf.csv ../score_lookup/5848148.csv 5848148_swap_matrix.csv
cd ../score_lookup
./score_lookup.exe ../gm.csv ../gf.csv ../score_lookup/5848148.csv ../create_score_lookup/5848148_swap_matrix.csv .\5848148_best_swap_mapping.csv ./5839988_best_swap_swap_matrix.csv
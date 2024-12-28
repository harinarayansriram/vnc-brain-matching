#!/bin/bash

#SBATCH --job-name=vnc_matching_parallel       # Job name
#SBATCH --output=%x-%j.out                       # Output file
#SBATCH --error=%x-%j.err                        # Error file
#SBATCH --time=12:00:00                          # Time limit (12  hours)
#SBATCH --signal=R:USR1@90                       # Send SIGUSR1 90 seconds before the end of the time limit
#SBATCH --signal=B:USR2@30                       # Send SIGUSR2 30 seconds before the end of the time limit
#SBATCH --requeue                                # Enable job requeuing

#SBATCH --qos=standard
#SBATCH --account=bader

#SBATCH --mem=64G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32

#SBATCH --profile task

module load bright
module load gcc/11.2.0


trap 'scontrol requeue $SLURM_JOB_ID' USR2

# Start of the job
echo "Job started at $(date)" >> %x-%j.out

# Run the program
gcc -O3 -Wall -lm -fopenmp xoshiro.c heap.c utils.c interrupts.c hungarian.c hungarian-subset.c score_lookup.c -o score_lookup
gcc -O3 -Wall -lm -fopenmp parallel_create_score_lookup.c -o parallel_create_score_lookup

./parallel_create_score_lookup ./gm.csv ./gf.csv ./5848956_best_swap_mapping.csv ./5848956_swap_matrix.csv
./score_lookup ./gm.csv ./gf.csv ./5848956_best_swap_mapping.csv ./5848956_swap_matrix.csv ./5848956_best_swap_mapping.csv ./5839988_best_swap_swap_matrix.csv &
wait
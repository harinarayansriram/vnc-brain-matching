import pandas as pd

# Read male connectome from male_connectome.csv
male_df = pd.read_csv("male_connectome_graph.csv")
male_df = male_df[["From Node ID", "To Node Id"]].stack()

# print the length of the number of unique nodes
unique_nodes_male = male_df.unique().size
print("Number of unique nodes in Male connectome:", unique_nodes_male)


# Read female connectome from female_connectome.csv
female_df = pd.read_csv("female_connectome_graph.csv")
female_df = female_df[["From Node ID", "To Node Id"]].stack()

# print the length of the number of unique nodes
unique_nodes_female = female_df.unique().size
print("Number of unique nodes in Female connectome:", unique_nodes_female)

if unique_nodes_male == unique_nodes_female:
    print("The number of unique nodes in male and female connectomes are equal.")
else:
    print("Error! The number of unique nodes in male and female connectomes are not equal.")
# Run all examples script with name example_*.sh iteratively

for example in $(find example/ -name example_*.sh); do
    echo "Run example: ${example}"
    bash ${example}
done

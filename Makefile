install:
	./tests/e2e-slurm/install-babs.sh
e2e: clean
	datalad remove ./testdata/babs_test_project/toybidsapp-container
	./tests/e2e-slurm/main.sh

# TODO testdata variable
clean:
	rm -rf .testdata

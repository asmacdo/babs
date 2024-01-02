install:
	./tests/e2e-slurm/install-babs.sh

e2e: clean
	./tests/e2e-slurm/main.sh

# TODO testdata variable
clean:
	datalad remove -d .testdata/babs_test_project/toybidsapp-container --reckless availability || true
	rm -rf .testdata

logs:
	cat .testdata/ci-logs/*

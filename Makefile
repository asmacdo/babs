install:
	./tests/e2e-slurm/install-babs.sh

e2e: clean
	./tests/e2e-slurm/main.sh

# TODO testdata variable
clean:
	podman stop slurm 2>/dev/null || true
	[ -e .testdata/babs_test_project/toybidsapp-container ] && \
		datalad remove -d .testdata/babs_test_project/toybidsapp-container --reckless kill || :
	rm -rf .testdata

logs:
	cat .testdata/ci-logs/*

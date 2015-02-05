SRCDIR = ./cider

analyze:
	prospector --profile .cider.yaml --ignore-paths src

test:
	py.test --maxfail 1 tests

clean:
	rm -rf ./build "$(SRCDIR)/*.pyc" "$(SRCDIR)/*.so"

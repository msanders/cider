SRCDIR = ./cider

analyze:
	prospector -T --profile=.cider.yaml

test:
	py.test tests

clean:
	rm -rf ./build "$(SRCDIR)/*.pyc" "$(SRCDIR)/*.so"

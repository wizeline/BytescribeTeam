packing:
	mkdir -p lambda_package
	cp src/lambda_function.py lambda_package/lambda_function.py
	pip install --platform manylinux2014_x86_64 --only-binary=:all: --target=lambda_package -r src/requirements.txt
	cd lambda_package; timestamp=$$(date +'%Y%m%d-%H%M%S'); zip -r ../build/lambda_package_$${timestamp}.zip .
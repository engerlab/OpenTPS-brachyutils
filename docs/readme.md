# How to build the doc ?

1. Install sphinx: 
``` 
pip install -U Sphinx 
``` 

2. Install fancy sphinx theme 
``` 
pip install sphinx-rtd-theme 
``` 

3. Install UML diagram extension 
``` 
sudo apt-get install graphviz 
pip install sphinx-pyreverse 
``` 

4. Build the API (only required if new files were added)

```
cd docs
sphinx-apidoc -o source/ ../
```

5. Build the html

```
make html
```
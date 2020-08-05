python -m ensurepip --default-pip
SET PYTHONPATH=
SET PYTHONHOME=%OSGEO4W_ROOT%\apps\Python37
PATH %OSGEO4W_ROOT%\apps\Python37;%OSGEO4W_ROOT%\apps\Python37\Scripts;%PATH%
python -m pip install --upgrade pip
pip install flask


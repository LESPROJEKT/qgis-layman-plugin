SET PYTHONPATH=
SET PYTHONHOME=%OSGEO4W_ROOT%\apps\Python37
PATH %OSGEO4W_ROOT%\apps\Python37;%OSGEO4W_ROOT%\apps\Python37\Scripts;%PATH%
python -m ensurepip --default-pip
python -m pip install --upgrade pip
python -m pip install flask
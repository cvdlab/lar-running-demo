


packages = []
packages.extend(['collections', 'scipy', 'numpy', 'pyplasm', 'time']) # LAR
packages.extend(['sys', 'logging', 'simplejson', 'json', 'requests', 'termcolor']) # mtx-accel
packages.extend(['png', 'matplotlib', 'struct']) # pngstack


try:
    return __import__(package)
except ImportError:
    return None
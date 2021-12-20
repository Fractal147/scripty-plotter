from setuptools import setup

setup(
    name='scripty_plotter',
    version='0.1.0',    
    description='Wrapper to make repetetive plots easier',
    url='https://github.com/Fractal147/scripty-plotter',
    author='Andrew Witty',
    author_email='andrew.witty@gmail.com',
    license='MIT License',
    #package_dir = {'' : "module"},
    #packages=['scripty_plotter'],
    py_modules=['scripty_plotter'],
    install_requires=[
                      'pandas',
                      'kaleido==0.1.0.post1'                     
                      ],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Operating System :: POSIX :: Linux :: Windows',        
        'Programming Language :: Python :: 3.9',
    ],
)
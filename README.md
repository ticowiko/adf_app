# Getting started

We start the same way we start any python project, by creating a virtual env and installing the core package. I highly recommend using python3.7 for your virtual env, as other versions will cause compatibility issues with the AWS implementer. In addition, make sure to properly set your `PYSPARK_PYTHON` path for full spark support :

```shell
mkvirtualenv adf -p `which python3.7`
export PYSPARK_PYTHON=`which python3`
pip install adf
```

To help us get started, the ADF package comes with a command that will initialize a work folder for us:

```shell
init-adf-work-folder.py adf_wksp
```

This will initialize a work folder called adf_wksp with everything we need to get started:

```
adf_wksp/
├── config
│   ├── flows
│   │   └── ...
│   └── implementers
│       └── ...
├── data_samples
│   └── test.csv
├── local_implementers
│   └── logs
├── scripts
│   └── ...
├── setup.py
└── src
    └── flow_operations
        ├── __init__.py
        └── operations.py
```

Finally, we can set up the web server very simply using :

```shell
git clone git@github.com:ticowiko/adf_app.git
cd adf_app
source init.sh
export ADF_WORKING_DIR=/absolute/path/to/adf_wksp/
python manage.py runserver
```

**Make sure to replace the path in the export command with the actual path to your adf_wksp folder.** You can then head over to http://localhost:8000/ and you should be greeted with a login page. The super top secret credentials you need to enter here are:

```
Username: admin
Password: admin
```

You should then be greeted with the home page with a form at the top to let you upload your ADF configurations.

# A simple example

You can configure your first ADF using the configuration files already present in our `adf_wksp` folder:

```
Name: local-simple-test
Implementer config file: config/implementers/implementer.local-multi-layer.sqlite.yaml
Flow config file: config/flows/flows.simple.default-flow-control.yaml
```

If all goes well, you should see a new ADF configuration appear in the left hand table. Hit the accompanying explore button to start working on your very first ADF, and you should land on the command tab. To actually run the ADF, hit the `Setup Implementer` button, then the `Setup Flows` button. After the 2 commands have succeeded, you should have the following structure inside your `local_implementers` folder in your `adf_wksp` directory :

```
local_implementers/
├── logs
└── multi_layer_sqlite
    ├── default
    ├── expose.db
    ├── heavy
    │   └── simple-default
    │       └── combination-flow
    │           └── combination-step
    │               └── default
    ├── light
    │   └── simple-default
    │       ├── flow-0
    │       │   ├── landing-step
    │       │   │   └── default
    │       │   └── meta-step
    │       │       └── default
    │       └── flow-1
    │           ├── landing-step
    │           │   └── default
    │           └── meta-step
    │               └── default
    ├── logs
    └── state.db
```

In your `adf_wksp` folder, copy some data samples into the landing steps so your orchestrator has something to work with :

```shell
cp data_samples/test.csv local_implementers/multi_layer_sqlite/light/simple-default/flow-0/landing-step/default/
cp data_samples/test.csv local_implementers/multi_layer_sqlite/light/simple-default/flow-1/landing-step/default/
```

Finally, hit the `Orchestrate (Synchronous)` button. You can follow batch submission in the `STDOUT` portion of the page. You can also head over to the `DAG state` tab to see your batches coming down the pipe by repeatedly hitting the `Refresh` button.

Synchronous orchestration stops automatically when there are no more batches to process, so when the command is done running you can explore your processed data. You will find newly created CSVs in the `light` and `heavy` layers, as well as new rows in the tables in your `expose.db` sqlite database.

If the Django server occasionally fails while complaining of `Too many open files`, you can simply increase your system resources to accommodate this. On most linux machines, the following command will do the trick :

```shell
ulimit -Sn 10240
```

# AWS implementer specificities

Before using the `config/implementers/implementer.aws.yaml` implementer configuration, you should set up a few things :

1) Ensure that you have valid AWS credentials in your `.aws` folder. The user must have near unlimited rights as you will be creating a vast array of resources across many AWS services.
2) In the same shell that launches the server, set a default AWS region by setting the corresponding environment variable : `export AWS_DEFAULT_REGION=YOUR-DEFAULT-REGION`.
3) In the same shell that launches the server, set the environment variables that will be used to initialize the admin passwords for your RDS and Redshift instances : `export RDS_PW=YOUR-RDS-PW` and `export REDSHIFT_PW=YOUR-REDSHIFT-PW`.

Once this is done, you can set up an ADF configuration as before, this time using the `implementer.aws.yaml` implementer config file, and any flow configuration file of your choosing. It is highly advised to use the `Prebuilt Config` functionality when using the AWS implementer. To do so :

1) Run the `Setup Implementer` command and wait for it to complete. This will likely take about 20 to 30 minutes, as we do not simply request resource creation but actually wait for the resources to be fully available.
2) Run the `Prebuilt Config` command. This will trigger a download of a newly constructed implementer configuration file. This implementer configuration points directly to the adresses of the newly created resources, rather than refer to them solely by layer name.
3) Close your current ADF configuration to get back to the homepage, and create a new one, using the same flow configuration file as before but this time using the implementer configuration file you just downloaded.
4) In your new ADF configuration, run the `Setup Flows` command, then the `Orchestrate (asynchronous)` command. Make sure to use the **asynchronous** orchestrator.

There are two advantages to using this prebuilt configuration :

1) Most critically, it requires far fewer permissions to run, not only for the orchestrator but also for the deployed data layers.
2) It runs much more quickly and smoothly on the orchestrator, as it can much more easily connect to your AWS resources.

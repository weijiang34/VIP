#!/bin/bash
echo "INFO: Creating conda env: vip ..."
conda create -n vip -c bioconda -c conda-forge seqkit checkv barrnap pandas
WORKING_DIR=$(pwd)
CONDA_ENVS_PATH=$(conda info | grep 'envs directories' | cut -d':' -f2 | sed 's/^ //')
CONDA_PATH=$(conda info | grep 'envs directories' | cut -d':' -f2 | sed 's/^ //' | sed 's/\/envs$//')

# CAT and its dependencies
echo "INFO: [1/4] Installing CAT_pack ..."
if [ ! -d $WORKING_DIR/dependencies/CAT_pack ]; then
    cd dependencies
    git clone https://github.com/MGXlab/CAT_pack.git
    cd ..
fi
# download and unpack CAT nr database
echo -e "\tInstalling CAT_pack_nr_db ..."
if [ ! -d $WORKING_DIR/dependencies/CAT_pack_nr_db ]; then
    cd dependencies
    mkdir CAT_pack_nr_db
    cd CAT_pack_nr_db
    wget -c tbb.bio.uu.nl/tina/CAT_pack_prepare/20240422_CAT_nr.tar.gz
    tar -xvzf 20240422_CAT_nr.tar.gz
    cd ../..
fi

# install virsorter2, only tool path check, no db check
echo "INFO: [2/4] Installing Virsorter2 ..."
ENV_NAME="vs2"
if conda info --envs | grep -q -w "$ENV_NAME"; then
    echo -e "\tEnv: '$ENV_NAME' already exists."
    if [ ! -d $WORKING_DIR/dependencies/vs2_db ]; then
        cd $WORKING_DIR/dependencies
        rm -rf vs2_db
        source $CONDA_PATH/bin/activate vs2 
        virsorter setup -d vs2_db -j 4
        conda deactivate
        cd ..
    fi
else
    echo -e "\tEnv: '$ENV_NAME' not existed, creating..."
    # create new environment
    conda create -n $ENV_NAME -c conda-forge -c bioconda virsorter=2 --yes
    if [ $? -eq 0 ]; then
        echo -e "\tEnv: '$ENV_NAME' created."
        echo -e "\tInstalling Virsorter2 database ..."
        cd $WORKING_DIR/dependencies
        rm -rf vs2_db
        source $CONDA_PATH/bin/activate vs2 
        virsorter setup -d vs2_db -j 4
        conda deactivate
        cd ..
    else
        echo -e "\tEnv: '$ENV_NAME' creation failed."
    fi
fi
# install genomad, both toll_path and db check
echo "INFO: [3/4] Installing GeNomad ..."
ENV_NAME="genomad"
if conda info --envs | grep -q -w "$ENV_NAME"; then
    echo -e "\tEnv: '$ENV_NAME' already exists."
    if [ -d ./dependencies/genomad_db ]; then
        rm -r ./dependencies/genomad_db
    fi
    source $CONDA_PATH/bin/activate genomad
    genomad download-database ./dependencies/
    conda deactivate
else
    echo -e "\tEnv: '$ENV_NAME' not existed, creating..."
    # create new environment
    conda create -n $ENV_NAME -c conda-forge -c bioconda genomad --yes
    if [ $? -eq 0 ]; then
        echo -e "\tEnv: '$ENV_NAME' created."
        if [ -d ./dependencies/genomad_db ]; then
            rm -r ./dependencies/genomad_db
        fi
        mkdir ./dependencies/genomad_db
        source $CONDA_PATH/bin/activate genomad
        genomad download-database ./dependencies/
        conda deactivate
    else
        echo -e "\tEnv: '$ENV_NAME' creation failed."
    fi
fi

# install viralm, only tool_path check
echo "INFO: [4/4] Installing ViraLM ..."
ENV_NAME="viralm"
if conda info --envs | grep -q -w "$ENV_NAME"; then
    echo -e "\tEnv: '$ENV_NAME' already exists."
    if [ ! -d $WORKING_DIR/dependencies/ViraLM/model ]; then
        cd $WORKING_DIR/dependencies/ViraLM
        source $CONDA_PATH/bin/activate viralm
        # download and setup the model
        gdown --id 1EQVPmFbpLGrBLU0xCtZBpwvXrtrRxic1
        tar -xzvf model.tar.gz -C .
        rm model.tar.gz
        conda deactivate
    fi
else
    if [ ! -d ViraLM ]; then
        cd $WORKING_DIR/dependencies
        git clone https://github.com/ChengPENG-wolf/ViraLM.git
        cd ViraLM
        # install and activate environment for ViraLM
        ENV_NAME="viralm"
        echo -e "\tEnv: '$ENV_NAME' not existed, creating..."
        # create new environment
        conda env create -f viralm.yaml -n viralm --yes
        if [ ! -d $WORKING_DIR/dependencies/ViraLM/model ]; then
            echo -e "\tEnv: '$ENV_NAME' created."
            source $CONDA_PATH/bin/activate viralm
            # download and setup the model
            gdown --id 1EQVPmFbpLGrBLU0xCtZBpwvXrtrRxic1
            tar -xzvf model.tar.gz -C .
            rm model.tar.gz
            conda deactivate
        cd ../..
        else
            echo -e "\tEnv: '$ENV_NAME' creation failed."
        fi
    fi
fi

# tool path check and env variables settings
if [ -f $WORKING_DIR/src/envs.py ];then
    rm $WORKING_DIR/src/envs.py
fi
if [ -f $WORKING_DIR/dependencies/CAT_pack/CAT_pack/CAT_pack ]; then    # CAT_pack
    echo -e "CAT_PACK_PATH = \"${WORKING_DIR}/dependencies/CAT_pack/CAT_pack/CAT_pack\"" >> $WORKING_DIR/src/envs.py
else
    echo "CAT_PACK_PATH = " >> $WORKING_DIR/src/envs.py
fi
if [ -f $CONDA_ENVS_PATH/vs2/bin/virsorter ]; then    # Virsorter2
    echo -e "VIRSORTER2_PATH = \"${CONDA_ENVS_PATH}/vs2/bin/virsorter\"" >> $WORKING_DIR/src/envs.py
else 
    echo "VIRSORTER2_PATH = " >> $WORKING_DIR/src/envs.py
fi
if [ -f $CONDA_ENVS_PATH/genomad/bin/genomad ]; then  # genomad
    echo -e "GENOMAD_PATH = \"${CONDA_ENVS_PATH}/genomad/bin/genomad\"" >> $WORKING_DIR/src/envs.py
else 
    echo "GENOMAD_PATH = " >> $WORKING_DIR/src/envs.py
fi
if [ -f $WORKING_DIR/dependencies/ViraLM/viralm.py ]; then  # genomad
    echo -e "VIRALM_PATH = \"${WORKING_DIR}/dependencies/ViraLM/viralm.py\"" >> $WORKING_DIR/src/envs.py
else 
    echo "VIRALM_PATH = " >> $WORKING_DIR/src/envs.py
fi

# db path check and env variables settings
if [ -d $WORKING_DIR/dependencies/CAT_pack_nr_db ]; then    # CAT_pack_nr_db
    echo -e "CAT_PACK_DB_PATH = \"${WORKING_DIR}/dependencies/CAT_pack_nr_db\"" >> $WORKING_DIR/src/envs.py
else
    echo "CAT_PACK_DB_PATH = " >> $WORKING_DIR/src/envs.py
fi
if [ -d $WORKING_DIR/dependencies/genomad_db ]; then    # genomad_db
    echo -e "GENOMAD_DB_PATH = \"${WORKING_DIR}/dependencies/genomad_db\"" >> $WORKING_DIR/src/envs.py
else 
    echo "GENOMAD_DB_PATH = " >> $WORKING_DIR/src/envs.py
fi

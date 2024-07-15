import os
import pandas as pd
import envs

CONDA_PATH = envs.CONDA_PATH
STROBEALIGN_PATH = envs.STROBEALIGN_PATH
SAMTOOLS_PATH = envs.SAMTOOLS_PATH
FEATURECOUNTS_PATH = envs.FEATURECOUNTS_PATH

def indexing(prj_dir, threads=4):
    os.makedirs(os.path.join(prj_dir,"Abundance"), exist_ok=True)
    os.makedirs(os.path.join(prj_dir,"Abundance","jobs"), exist_ok=True)
    os.makedirs(os.path.join(prj_dir,"Abundance","logs"), exist_ok=True)

    fasta = os.path.join(prj_dir,"Abundance","rep_contigs.fasta")
    faidx = os.path.join(prj_dir,"Abundance","rep_contigs.fa.fai")
    gtf = os.path.join(prj_dir,"Abundance","rep_contigs.gtf")
    job = os.path.join(prj_dir,"Abundance","jobs", "indexing.pbs")
    logs = os.path.join(prj_dir,"Abundance","logs")
    pbs_header = [
        "#!/bin/bash",

        "# Job Name:",
        "#PBS -N indexing",

        "# Project Info:",
        "#PBS -P mp96",
        "#PBS -l storage=gdata/oo46+gdata/mp96",

        "# Log Output:",
        f"#PBS -o {logs}/indexing.o",
        f"#PBS -e {logs}/indexing.e",
        "#PBS -j oe",

        "# Mailing:",
        "#PBS -m abe",
        "#PBS -M 379004663@qq.com",
        
        "# Resources Allocation:",
        "#PBS -q normalsl",
        "#PBS -l walltime=2:00:00",
        "#PBS -l mem=120GB",
        f"#PBS -l ncpus={threads}",
        "#PBS -l jobfs=2GB",
    ]
    bash_commands = [
        f"source {CONDA_PATH}/bin/activate vip\n",
        f"cp {prj_dir}/OVU/rep_contigs.fasta {prj_dir}/Abundance/\n",
        f"{STROBEALIGN_PATH} --create-index -t {threads} -r 150 {fasta}\n",
        f"{SAMTOOLS_PATH} faidx {fasta} -o {faidx}\n",
        f"awk \'BEGIN {{FS=\"\\t\"}}; {{print $1\"\\tclustering\\tcontig\\t1\\t\"$2\"\\t\"$2\"\\t+\\t1\\tcontig_id \\\"\"$1\"\\\"\"}}\' {faidx} > {gtf}\n",
    ]
    os.makedirs(os.path.dirname(job), exist_ok=True)
    os.makedirs(logs, exist_ok=True)
    with open(job, 'w') as f:
        f.writelines([line + "\n" for line in pbs_header] + bash_commands)

def chunk_dataframe(df: pd.DataFrame, size: int=10):
    num_of_chunks = len(df) // size
    remaining_data = len(df) % size
    chunks = []
    for i in range(num_of_chunks):
        chunk = df.iloc[i*size:(i+1)*size, :]
        chunks.append(chunk)
    if remaining_data!= 0:
        chunk = df.iloc[num_of_chunks*size:, :]
        chunks.append(chunk)
    return chunks

def mapping(prj_dir, manifest, threads=4):
    os.makedirs(os.path.join(prj_dir,"Abundance"), exist_ok=True)
    os.makedirs(os.path.join(prj_dir,"Abundance","jobs"), exist_ok=True)
    os.makedirs(os.path.join(prj_dir,"Abundance","logs"), exist_ok=True)
    os.makedirs(os.path.join(prj_dir,"Abundance","out"), exist_ok=True)

    df = pd.read_csv(manifest, header=None, names=["fileHeader", "fq1", "fq2"], index_col=None, sep='\t')
    chunks = chunk_dataframe(df, size=10)
    fasta = os.path.join(prj_dir, "Abundance", "rep_contigs.fasta")
    gtf = os.path.join(prj_dir,"Abundance","rep_contigs.gtf")
    
    for chunk in chunks:
        header_list = chunk["fileHeader"].tolist()
        fq1_list = chunk["fq1"].tolist()
        fq2_list = chunk["fq2"].tolist()
        header_pair_list = [header+"|"+fq1+"|"+fq2 for header,fq1,fq2 in zip(header_list,fq1_list,fq2_list)]
        job = os.path.join(prj_dir,"Abundance","jobs", f"mapping_{chunk.index.to_list()[0]+1}_{chunk.index.to_list()[-1]+1}.pbs")
        logs = os.path.join(prj_dir,"Abundance","logs")
        pbs_header = [
            "#!/bin/bash",

            "# Job Name:",
            f"#PBS -N mapping_{chunk.index.to_list()[0]+1}_{chunk.index.to_list()[-1]+1}",

            "# Project Info:",
            "#PBS -P mp96",
            "#PBS -l storage=gdata/oo46+gdata/mp96",

            "# Log Output:",
            f"#PBS -o {logs}/mapping_{chunk.index.to_list()[0]+1}_{chunk.index.to_list()[-1]+1}.o",
            f"#PBS -e {logs}/mapping_{chunk.index.to_list()[0]+1}_{chunk.index.to_list()[-1]+1}.e",
            "#PBS -j oe",

            "# Mailing:",
            "#PBS -m abe",
            "#PBS -M 379004663@qq.com",
            
            "# Resources Allocation:",
            "#PBS -q normalsl",
            "#PBS -l walltime=2:30:00",
            "#PBS -l mem=120GB",
            f"#PBS -l ncpus={threads}",
            "#PBS -l jobfs=2GB",
        ]
        bash_commands = [
            f"source {CONDA_PATH}/bin/activate vip",
            "header_pair_list=(",
            "{}".format('\n'.join(f'"{item}"' for item in header_pair_list)),
            ")",
            'for header_pair in ${header_pair_list[@]};do',
            "\theader=$(echo $header_pair | cut -d \'|\' -f1)",
            "\tfq1=$(echo $header_pair | cut -d \'|\' -f2)",
            "\tfq2=$(echo $header_pair | cut -d \'|\' -f3)",
            f"\tfasta={fasta}",
            f"\tgtf={gtf}",
            f"\tout_dir={os.path.join(prj_dir,'Abundance', 'out')}/$header",
            f"\tbam={os.path.join(prj_dir,'Abundance', 'out')}/$header/\"$header\"_sorted.bam",
            f"\tstat={os.path.join(prj_dir,'Abundance', 'out')}/$header/\"$header\"_stat.txt",
            f"\tcount={os.path.join(prj_dir,'Abundance', 'out')}/$header/\"$header\"_count.tsv",
            f"\tmkdir -p $out_dir",
            "\techo \"$header mapping started.\"",
            f"\t{STROBEALIGN_PATH} --use-index $fasta -t {threads} $fq1 $fq2 | {SAMTOOLS_PATH} sort -T $out_dir -o $bam -@ {threads}",
            f"\t{SAMTOOLS_PATH} index $bam -@ {threads}",
            f"\t{SAMTOOLS_PATH} flagstat $bam -@ {threads} > $stat",
            f"\t{FEATURECOUNTS_PATH} -p -t contig -g contig_id -a $gtf -o $count -T {threads} $bam",
            f"\techo \"$header mapping finished!\"",
            f"\techo \"{'-'*100}\"",
            # f"\tbreak",
            "done",
        ]
        with open(job, 'w') as f:
            f.writelines([line + "\n" for line in pbs_header] + [line + "\n" for line in bash_commands])

def check(prj_dir, manifest):
    manifest = pd.read_table(manifest, header=None, names=["fileHeader", "fq1", "fq2"])
    mapping = pd.DataFrame({
        "fileHeader": manifest["fileHeader"],
        "mapping": False,
        "_count.tsv": False,
        "_count.tsv.summary": False,
        "_sorted.bam": False,
        "_sorted.bam.bai": False,
        "_stat.txt": False
    })
    def check_single(s, prj_dir):
        columns_to_check = ["_count.tsv", "_count.tsv.summary", "_sorted.bam", "_sorted.bam.bai", "_stat.txt"]
        for col in columns_to_check:
            s[col] = os.path.isfile(os.path.join(prj_dir, "Abundance", "out", s["fileHeader"], s["fileHeader"]+col))
        if s[columns_to_check].all():
            s["mapping"] = True
        return s
    mapping = mapping.apply(lambda s: check_single(s, prj_dir=prj_dir), axis=1)
    mapping.to_csv(os.path.join(prj_dir, "Abundance", "mapping_check.csv"),index=None)
    return mapping

def count_matrix(prj_dir, manifest):
    # get all
    def get_all_count(prj_dir, manifest):
        mapping_check = check(prj_dir=prj_dir, manifest=manifest)
        all_count = pd.DataFrame()
        for idx, row in mapping_check.iterrows():
            if row["mapping"]==False:
                print(f"{idx}\t{row['fileHeader']}\tNo file")
            else:
                current_count = pd.read_table(
                    os.path.join(prj_dir, "Abundance", "out", row["fileHeader"], f"{row['fileHeader']}_count.tsv"),header=1,
                    names = ['contig', 'Chr', 'Start', 'End', 'Strand','Length', row["fileHeader"]],
                )
                if all_count.shape[1]==0:
                    all_count = current_count
                else:
                    all_count = pd.merge(all_count, current_count, how='left')
        all_count.to_csv(os.path.join(prj_dir, "Abundance", "all_count.csv"), index=None)
        return all_count
    
    def get_RPK(all_count):
        RPK = all_count.apply(lambda x: x/all_count.index.get_level_values("Length")*1e3, axis=0)
        return RPK
    def get_FPKM(all_count, RPK):
        FPKM = RPK.apply(lambda x: x/all_count[x.name].sum()*1e6,axis=0)
        return FPKM
    def get_TPM(RPK):
        TPM = RPK.apply(lambda x: x/x.sum()*1e6,axis=0)
        return TPM

    all_count = get_all_count(prj_dir, manifest)
    all_count.to_csv(os.path.join(prj_dir, "Abundance", "all_count.csv"), index=None)
    all_count = all_count.set_index(['contig', 'Chr', 'Start', 'End', 'Strand','Length']).astype(int)
    
    RPK = get_RPK(all_count)
    FPKM = get_FPKM(all_count, RPK).reset_index()
    TPM = get_TPM(RPK).reset_index()
    
    FPKM.to_csv(os.path.join(prj_dir,"Abundance","all_FPKM.csv"), index=None)
    TPM.to_csv(os.path.join(prj_dir,"Abundance","all_TPM.csv"), index=None)

if __name__=="__main__":
    pass
    # indexing(prj_dir="/g/data/oo46/wj6768/Healthy_Virome_HOAM_ORAL", threads=THREADS)
    # mapping(prj_dir=PRJ_DIR, 
    #         manifest=os.path.join(PRJ_DIR, "Abundance", "manifest.tsv"), 
    #         threads=THREADS)
    # check(prj_dir=PRJ_DIR, manifest=os.path.join(PRJ_DIR, "Abundance", "manifest.tsv"))
    # count_matrix(prj_dir=PRJ_DIR, manifest=os.path.join(PRJ_DIR, "Abundance", "manifest.tsv"))
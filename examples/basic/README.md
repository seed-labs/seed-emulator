一共有1230个节点和2250节点两个规模的骨干网络，请在autocoder1.py中第168行修改路径确定哪个网络。
运行的时候看报什么错就运行对应安装的包。理论上安装一下networkx和pickle即可：

conda install networkx

conda install pickle


然后执行build和up命令分别用以下两个：
#分批构造

export DOCKER_BUILDKIT=0; docker compose config --services | xargs -n300 docker compose build

#分批up

export DOCKER_BUILDKIT=0; docker compose config --services | xargs -n100 docker compose up -d
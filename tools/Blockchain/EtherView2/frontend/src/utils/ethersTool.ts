import {ethers, providers} from "ethers";
// import {useGlobalStore} from "@/store"

// const globalStore = useGlobalStore()
// const provider_url = globalStore.web3Url
const provider_url = "http://192.168.254.128:8545"

// const provider_url = "http://10.1.101.81:8545"

export function get_provider(): providers.BaseProvider {
    return ethers.getDefaultProvider(provider_url);
}

export async function get_blocks_total(provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();
    return await provider.getBlockNumber();
}


export async function get_blocks(
    provider?: providers.BaseProvider,
    start = 0,
    end = Infinity,
    reverse = false,
    batchSize = 1000
) {
    provider = provider ?? get_provider();

    const blocks: any[] = [];
    const latestBlockNumber = await provider.getBlockNumber();

    if (latestBlockNumber <= 0) return;

    // 参数合法化
    if (start < 0) start = 0;
    if (end == null || end > latestBlockNumber) end = latestBlockNumber;

    // 处理 reverse 场景
    if (reverse) {
        const _end = latestBlockNumber - start;
        start = _end - (end - start);
        end = _end;
    }

    // 生成需要遍历的区块号数组（从 end 往 start 递减）
    const blockNumbers: number[] = [];
    for (let i = end; i >= start; i--) {
        blockNumbers.push(i);
    }

    // 按 batchSize 切分并并发请求
    for (let i = 0; i < blockNumbers.length; i += batchSize) {
        const slice = blockNumbers.slice(i, i + batchSize); // 本批次的区块号

        // 并发获取每个区块（含交易）
        const batchPromises = slice.map((num) => provider!.getBlockWithTransactions(num));
        const rawBlocks = await Promise.all(batchPromises);

        // 对每个区块执行 rebuildBlockData（如果该函数本身是异步的，需要再并发）
        const rebuildPromises = rawBlocks.map((blk) => rebuildBlockData(provider!, blk));
        await Promise.all(rebuildPromises);

        // 将处理好的区块加入结果数组（保持原来的顺序）
        blocks.push(...rawBlocks);
    }

    return {blocks, total: latestBlockNumber};
}

export async function show_all_blocks(blocks: any[]) {
    return await show_current_block(blocks, 0)
}

export async function show_all_transactions(blocks: any[]) {
    let transactions = [];
    for (let block of blocks) {
        for (const tx of block.transactions) {
            tx.eth = ethers.utils.formatEther(tx.value)
            tx.gasPriceGwei = ethers.utils.formatUnits(tx.gasPrice, 'gwei')
            tx.timestamp = block.timestamp
        }
        transactions.push({
            [block.block_number]: block.transactions,
        })
    }
    // console.log("======================");
    // console.log('all_transactions: ', transactions)

    return transactions
}

export async function show_current_block(blocks: any[], limit = 20) {
    let i = 0;
    let _blocks = [];
    if (limit > 0) {
        i = blocks.length - limit;
    }
    i = i < 0 ? 0 : i;
    for (i; i < blocks.length; i++) {
        let block = blocks[i];

        _blocks.push(block);
    }

    // console.log("======================");
    // console.log(`current_block limit ${limit}: ${JSON.stringify(_blocks)}`);

    return _blocks;
}

export async function show_current_transactions_by_time(blocks: any[], hour = 24) {
    let transactions: any[] = [];
    let pending_transactions: any[] = [];
    let len = blocks.length;
    let index = len - 1;
    let totalGasUsed = BigInt(0);
    let totalFees = BigInt(0);
    let transactionCount = 0;
    const time = Math.floor(Date.now() / 1000) - (hour * 60 * 60);

    while (index >= 0) {
        const block = blocks[index];
        if (block.timestamp < time) {
            console.log(`区块 ${block.number} 时间 ${new Date(block.timestamp * 1000)} 已超过24小时, 停止扫描`);
            break;
        }
        if (block && block.transactions) {
            const blockBaseFeePerGas = block.baseFeePerGas ? BigInt(block.baseFeePerGas) : BigInt(0);

            // 计算区块内每笔交易的费用
            for (const tx of block.transactions) {
                if (tx && tx.blockNumber === null) {
                    pending_transactions.push(tx);
                }
                if (tx.gasPrice && tx.gasLimit) {
                    // 方法1：使用实际的gasUsed（如果可用）
                    let txGasUsed = tx.gasUsed ? BigInt(tx.gasUsed) : BigInt(tx.gasLimit);

                    // 方法2：对于EIP-1559交易，使用更精确的计算
                    let txFee = BigInt(0);

                    if (tx.type === 2) {
                        // EIP-1559交易：gasUsed * (baseFee + priorityFee)
                        const maxPriorityFeePerGas = tx.maxPriorityFeePerGas ? BigInt(tx.maxPriorityFeePerGas) : BigInt(0);
                        const effectiveGasPrice = blockBaseFeePerGas + maxPriorityFeePerGas;
                        txFee = txGasUsed * effectiveGasPrice;
                    } else {
                        // 传统交易：gasUsed * gasPrice
                        txFee = txGasUsed * BigInt(tx.gasPrice);
                    }

                    totalGasUsed += txGasUsed;
                    totalFees += txFee;
                    transactionCount++;
                }
            }

            const tTransactions = block.transactions.map((tx: any) => ({
                ...tx,
                blockTimestamp: block.timestamp,
                humanTime: new Date(block.timestamp * 1000).toISOString()
            }));

            transactions.push(...tTransactions);
        }

        index--;
    }
    // console.log("======================");
    // console.log(`current_transactions time ${hour}H: ${JSON.stringify(transactions)})}`);
    // console.log(`current_pending_transactions time ${hour}H: ${JSON.stringify(pending_transactions)})}`);
    // console.log(`Fee: ${JSON.stringify(calculateFeeStats(totalFees, totalGasUsed, transactionCount))}`);

    return {transactions, pending_transactions}
}

export async function getPendingTxs(provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();

    let allPendingTxs: any[] = [];
    try {
        const txpoolContent = await provider.send("txpool_content");
        for (const [address, txs] of Object.entries(txpoolContent.pending)) {
            for (const [nonce, tx] of Object.entries(txs)) {
                allPendingTxs.push({
                    from: address,
                    to: tx.to,
                    hash: tx.hash,
                    nonce: parseInt(nonce),
                    value: ethers.utils.formatEther(tx.value),
                    gasPrice: ethers.utils.formatUnits(tx.gasPrice, 'gwei'),
                    gas: tx.gas,
                    input: tx.input
                });
            }
        }
    } catch (error) {
        console.error("Error fetching txpool content:", error);
    }
    return allPendingTxs
}

export async function show_current_transactions(
    provider?: providers.BaseProvider,
    limit = 20,
    batchSize = 1000
) {
    provider = provider ?? get_provider();

    let transactions: any[] = [];
    let blockNumber = await provider.getBlockNumber(); // 当前最高块号

    // 循环直到收集到足够的交易或没有更多块可查
    while (blockNumber >= 0 && transactions.length < limit) {
        // 生成本轮需要查询的块号列表（向后递减）
        const batchIndices: number[] = [];
        for (let i = 0; i < batchSize && blockNumber - i >= 0; i++) {
            batchIndices.push(blockNumber - i);
        }

        // 并发请求这些块
        const batchBlocks = await Promise.all(
            batchIndices.map((idx) => provider!.getBlockWithTransactions(idx))
        );

        // 按块号从新到旧的顺序依次合并交易
        for (const blk of batchBlocks) {
            if (blk && blk.transactions.length) {
                transactions = transactions.concat(blk.transactions);
                if (transactions.length >= limit) break; // 已够数，提前退出
            }
        }

        // 更新下一个待查询的块号
        blockNumber -= batchSize;
    }

    // 截取到用户要求的上限
    transactions = transactions.slice(0, limit);

    // 将 value（Wei）转为 Ether 方便阅读
    for (const tx of transactions) {
        tx.eth = ethers.utils.formatEther(tx.value);
    }

    return transactions;
}


export async function get_block(provider?: providers.BaseProvider, block_number: string) {
    provider = provider ?? get_provider();

    return await provider.getBlockWithTransactions(parseInt(block_number));
}

export async function get_GAS_price(provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();

    let price = await provider.getGasPrice()

    console.log("======================");
    console.log(`当前 Gas 价格：${ethers.utils.formatUnits(price, "gwei")} Gwei`);
}


export const get_balance = async (provider?: providers.BaseProvider, address: string) => {
    provider = provider ?? get_provider();

    let balance = await provider.getBalance(address);

    //console.log(address + ':' + ethers.utils.formatEther(balance));
    let eth_balance = ethers.utils.formatEther(balance, {commify: true});
    eth_balance = (+eth_balance).toPrecision(10);
    return eth_balance;
}

export const get_nonce = async (provider?: providers.BaseProvider, address: string) => {
    provider = provider ?? get_provider();

    return await provider.getTransactionCount(address, 'pending');
}


function calculateFeeStats(totalFees: any, totalGasUsed: any, transactionCount: any) {
    if (transactionCount === 0) {
        return {
            totalFees: BigInt(0),
            totalFeesETH: "0",
            averageFee: BigInt(0),
            averageFeeETH: "0",
            totalGasUsed: BigInt(0),
            transactionCount: 0,
            averageGasPerTx: 0
        };
    }

    const averageFee = totalFees / BigInt(transactionCount);
    const averageGasPerTx = Number(totalGasUsed) / transactionCount;

    return {
        // 原始值（wei）
        totalFees: totalFees.toString(),
        averageFee: averageFee.toString(),
        totalGasUsed: totalGasUsed.toString(),

        // 格式化值（ETH）
        totalFeesETH: ethers.utils.formatEther(totalFees),
        averageFeeETH: ethers.utils.formatEther(averageFee),

        // 统计信息
        transactionCount: transactionCount,
        averageGasPerTx: averageGasPerTx,

        // Gwei单位（便于阅读）
        totalFeesGwei: ethers.utils.formatUnits(totalFees, "gwei"),
        averageFeeGwei: ethers.utils.formatUnits(averageFee, "gwei")
    };
}

async function rebuildBlockData(provider?: providers.BaseProvider, block) {
    provider = provider ?? get_provider();

    block.block_number = block.number;
    block.txn = block.transactions.length;
    block.reward = ethers.BigNumber.from(0);
    block.time = block.timestamp;
    block.burntFee = block.baseFeePerGas.mul(block.gasUsed);
    block._baseFeePerGas = ethers.utils.formatUnits(block.baseFeePerGas, "gwei");
    block.gasUsed = block.gasUsed.toString();
    block.gasLimit = block.gasLimit.toString();
    block.time = timeTo(block.timestamp)
    for (let j = 0; j < block.txn; j++) {
        let hash = block.transactions[j].hash;
        let tx = await provider.getTransaction(hash);
        let tx_r = await provider.getTransactionReceipt(hash);
        // let gasPrice = ethers.utils.formatUnits(tx.gasPrice, "gwei");
        // let gasUsed = tx_r.gasUsed.toString();

        const gasPrice: ethers.BigNumber = tx.gasPrice ?? ethers.constants.Zero; // 若 undefined 则为 0
        const gasUsed: ethers.BigNumber = tx_r.gasUsed; // 已是 BigNumber

        block.reward = block.reward.add(gasPrice.mul(gasUsed));
    }
    block.reward =
        ethers.utils.formatUnits(block.reward.sub(block.burntFee), "ether") +
        " ETH";
    block.burntFee = ethers.utils.formatUnits(block.burntFee, "ether");
}

export function timeTo(timestamp: number) {
    let timeStr = ''
    let sec = Math.floor((Date.now() - timestamp * 1000) / 1000);
    if (sec < 0) {
        sec = 0
    }
    if (sec < 60) {
        timeStr = `${sec} secs ago`;
    } else {
        let min = Math.floor(sec / 60);
        if (min < 60) {
            timeStr = `${min} mins ago`;
        } else {
            let hour = Math.floor(min * 10 / 60) / 10;
            if (hour < 24) {
                timeStr = `${hour} hours ago`;
            } else {
                let day = Math.floor(hour * 10 / 24) / 10;
                timeStr = `${day} days ago`;
            }
        }
    }
    return timeStr
}
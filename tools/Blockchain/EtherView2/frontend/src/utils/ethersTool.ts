import {ethers, providers} from "ethers";
import {useGlobalStore} from "@/store"

const globalStore = useGlobalStore()
const provider_url = globalStore.web3Url
// const provider_url = "http://10.1.101.81:8545"
// const provider_url = "http://192.168.254.128:8545"
const BATCH_SIZE = 1000

export function get_provider(): providers.BaseProvider {
    return ethers.getDefaultProvider(provider_url);
}

export async function get_blocks_total(provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();
    return await provider.getBlockNumber();
}


export async function get_blocks_with_transactions(
    provider?: providers.BaseProvider,
    start = 0,
    end = Infinity,
    txn_limit = Infinity,
    reverse = false,
    batchSize = BATCH_SIZE
) {
    provider = provider ?? get_provider();

    const blocks: any[] = [];
    const transactions: any[] = [];
    const latestBlockNumber = await provider.getBlockNumber();

    if (latestBlockNumber <= 0) return {blocks, total: latestBlockNumber};

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
    if (batchSize > blockNumbers.length) {
        batchSize = blockNumbers.length
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
    for (const blk of blocks) {
        if (transactions.length > txn_limit) {
            break
        }
        const txCount = blk.transactions.length;
        const remainCount = txn_limit - transactions.length
        transactions.push(...blk.transactions
            .slice(Math.max(0, txCount - remainCount)) // 取最后 10 条（若不足则全部）
            .reverse())
    }

    return {blocks, transactions, total: latestBlockNumber};
}


export async function getPendingTxs(provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();

    let allPendingTxs: any[] = [];
    try {
        const txpoolContent = await provider.send("txpool_content");
        for (const [address, txs] of Object.entries(txpoolContent.pending)) {
            for (const [nonce, tx] of Object.entries(txs)) {
                allPendingTxs.push({
                    time: tx.time,
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

export async function countPendingTxLastHour(provider?: providers.BaseProvider): Promise<number> {
    provider = provider ?? get_provider();
    const allPendingTxs = await getPendingTxs(provider)
    let count = 0
    const now = Date.now();
    for (let tx of allPendingTxs) {
        if (tx.time) {
            const txTimeMs = Number(tx.time) * 1000;
            if (now - txTimeMs <= 60 * 60 * 1000) {
                count++;
            }
        } else {
            count++;
        }
    }

    return count
}

export async function calcFeesLast24h(provider?: providers.BaseProvider): Promise<{
    totalFeeWei: ethers.BigNumber;
    avgFeeWei: ethers.BigNumber;
    txCount: number;
}> {
    provider = provider ?? get_provider();
    const latestBlockNumber = await provider.getBlockNumber();
    const now = Math.floor(Date.now() / 1000); // 秒
    const cutoffTimestamp = now - 24 * 60 * 60; // 24 h 前的区块时间戳

    let totalFee = ethers.BigNumber.from(0);
    let txCount = 0;
    let blockNum = latestBlockNumber;

    // 循环向前遍历区块，直到时间早于 24
    while (blockNum >= 0) {
        const block = await provider.getBlockWithTransactions(blockNum);
        if (block.timestamp < cutoffTimestamp) {
            break;
        }

        // 收集本块所有交易哈希
        const txHashes = block.transactions.map((tx) => tx.hash);
        const receipts = await getReceipts(txHashes);

        for (const receipt of receipts) {
            // effectiveGasPrice 在 EIP‑1559 之后可直接获取；若不存在则回退到 gasPrice
            const gasPrice = receipt.effectiveGasPrice
                ? receipt.effectiveGasPrice
                : receipt.gasPrice || ethers.BigNumber.from(0);
            const fee = receipt.gasUsed.mul(gasPrice);
            totalFee = totalFee.add(fee);
            txCount++;
        }

        // 为防止一次性遍历过多区块（尤其是链较长），可自行设置上限
        // 这里示例每次向前 5000 个区块后强制退出（约 1‑2 天的区块数）
        if (latestBlockNumber - blockNum > 5000) break;

        blockNum--;
    }

    const avgFee = txCount > 0 ? totalFee.div(txCount) : ethers.BigNumber.from(0);
    return {totalFeeWei: totalFee, avgFeeWei: avgFee, txCount};
}

export async function get_transaction_info(hash: string, provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();
    const tx = await provider.getTransaction(hash);
    if (!tx) {
        console.log('未找到对应的交易');
        return {};
    }
    const receipt = await provider.getTransactionReceipt(hash);

    return {
        hash: tx.hash,
        from: tx.from,
        to: tx.to,
        value: ethers.utils.formatEther(tx.value),
        gasPrice: ethers.utils.formatUnits(tx.gasPrice, 'gwei') + ' gwei',
        nonce: tx.nonce,
        data: tx.data,
        blockNumber: tx.blockNumber,
        // 回执信息
        status: receipt ? (receipt.status === 1 ? 'Success' : 'Failed') : 'Pending',
        gasUsed: receipt ? receipt.gasUsed.toString() : null,
        cumulativeGasUsed: receipt ? receipt.cumulativeGasUsed.toString() : null,
        transactionIndex: receipt ? receipt.transactionIndex : null,
    }
}

export async function get_block(provider?: providers.BaseProvider, block_number: string) {
    provider = provider ?? get_provider();

    return await provider.getBlockWithTransactions(parseInt(block_number));
}

export async function get_blocks_24H(provider?: providers.BaseProvider, batchSize = BATCH_SIZE, includeTxs = true): Promise<ethers.providers.Block[]> {
    provider = provider ?? get_provider();

    // 1️⃣ 获取最新区块号
    const latestNumber = await provider.getBlockNumber();

    // 2️⃣ 计算时间阈值（Unix 秒）
    const now = Math.floor(Date.now() / 1000);
    const cutoff = now - 24 * 60 * 60;

    // 4️⃣ 二分查找最早满足条件的区块号
    let low = 0;
    let high = latestNumber;
    let startNumber = latestNumber; // 默认全部满足

    while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        const block = await provider.getBlock(mid);   // 只取时间戳即可
        if (Number(block.timestamp) < cutoff) {
            low = mid + 1;
        } else {
            startNumber = mid;
            high = mid - 1;
        }
    }

    const result: providers.Block[] = [];
    for (let start = startNumber; start <= latestNumber; start += batchSize) {
        let batchPayload = [];
        for (let n = start; n < start + batchSize; n++) {
            batchPayload.push({
                jsonrpc: "2.0",
                id: n,
                method: "eth_getBlockByNumber",
                params: [ethers.utils.hexValue(n), includeTxs],
            })
        }
        const response = await fetch(provider_url, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(batchPayload),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status} – ${response.statusText}`);
        }

        const rawResults: any[] = await response.json();

        // 5️⃣ 解析并再次过滤时间戳（防止节点返回的块时间略早）
        for (const raw of rawResults) {
            const block = raw.result as providers.Block;
            if (block && Number(block.timestamp) >= cutoff) {
                result.push(block);
            }
        }
    }

    // 按区块号升序返回（可自行改为降序）
    result.sort((a, b) => a.number - b.number);
    return result;
}

/**
 * 1️⃣ 网络利用率
 *    utilization = Σ(gasUsed) / Σ(gasLimit)
 */
export async function get_networkUtilization(blocks: ethers.providers.Block[]): Promise<string> {
    let totalUsed = ethers.BigNumber.from(0);
    let totalLimit = ethers.BigNumber.from(0);

    for (const b of blocks) {
        totalUsed = totalUsed.add(b.gasUsed);
        totalLimit = totalLimit.add(b.gasLimit);
    }

    if (totalLimit.isZero()) return 0;

    return `${(Number(totalUsed) * 10000 / Number(totalLimit) / 100).toFixed(8)}%`; // 如 78.34 (%)
}

export async function get_blocks_by_mevBuilders(blocks: ethers.providers.Block[], lastBlockNumber): Promise<string> {
    let count = 0;
    for (const b of blocks) {
        const proposer = (b as any).miner || (b as any).proposer;
        if (proposer) {
            count++;
        }
    }
    if (lastBlockNumber === 0) {
        return "0"
    }
    return (count * 100 / lastBlockNumber).toFixed(2) + '%';
}

export async function get_BurntFees(blocks: ethers.providers.Block[]): Promise<string> {
    let totalBurnWei = ethers.BigNumber.from(0);

    for (const block of blocks) {
        if (block.baseFeePerGas) {
            const baseFee = ethers.BigNumber.from(block.baseFeePerGas)
            const burn = baseFee.mul(block.gasUsed);
            totalBurnWei = totalBurnWei.add(burn);
        }
    }

    return `${Number(ethers.utils.formatEther(totalBurnWei)).toFixed(8)} ETH`;
}

export async function get_GAS_price(provider?: providers.BaseProvider) {
    provider = provider ?? get_provider();
    let price = await provider.getGasPrice()

    return `${ethers.utils.formatUnits(price, "gwei")} Gwei`
}

export const get_balance = async (provider?: providers.BaseProvider, address: string) => {
    provider = provider ?? get_provider();

    let balance = await provider.getBalance(address);

    let eth_balance = ethers.utils.formatEther(balance, {commify: true});
    eth_balance = (+eth_balance).toPrecision(10);
    return eth_balance;
}

export const get_nonce = async (provider?: providers.BaseProvider, address: string) => {
    provider = provider ?? get_provider();

    return await provider.getTransactionCount(address, 'pending');
}

async function rebuildBlockData(provider?: providers.BaseProvider, block: ethers.providers.Block) {
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
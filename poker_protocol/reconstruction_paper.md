# 可组合的隐私保持牌组重建

## 槽位语义绑定、跨密钥联合证明与 Lean 形式化

日期：2026-09-16
代码基线：`poker-protocol-proofs` 的 `ReconstructProof`
开源仓库：[poker_protocol](https://github.com/linqining/poker_protocol)

> **主张边界。** 本文的条件 UC 定理在随机预言机、Bayer--Groth 组件安全、
> 状态认证和字节级 refinement 假设下成立。Lean 机器检查 residual-carrier lineage、
> 聚合语义、跨密钥 Sigma、槽位 OR，以及生产组件保证到完整 reconstruction
> 语义的组合定理。组件计算安全和序列化 refinement 是显式安全假设，不是
> 未完成的 Lean proof goal。

## 摘要

心智扑克需要在下一局开始前重建牌组：上一局被玩家持有的牌应从牌组中精确移除，其余牌仍保持可继续洗牌的 ElGamal 密文。普通 shuffle argument 只证明输出是输入的重加密置换，不能证明某个槽位的明文属于 `{0,-m_i}`。因此 reconstruction 需要把 shuffle 隐藏性、跨密钥明文绑定和逐槽语义放进同一个证明系统。

本文分析的协议让每个玩家在共同聚合公钥 `P` 下提交逐槽贡献

```text
C_i = Enc_P(0; v_i) 或 Enc_P(-m_i; v_i),
```

其中负分支只能由一个经过状态认证的 owner-residual carrier 支持。证明由四个部分组成：对每个 residual carrier 的跨密钥联合 generalized-Schnorr proof；隐藏 residual-carrier-to-slot 映射的 Bayer--Groth shuffle proof；每个 canonical slot 的二分支 OR proof；以及对上下文、epoch、状态摘要、公钥、牌点和全部密文的 transcript 绑定。

在明确假设下，我们证明接受的证明包可提取满足逐槽语义和 exact coverage 的见证；重建后的槽位为原牌或 identity；每张认证 residual carrier 至多且恰好移除一次；协议在 `F_RECON` 理想功能下满足静态腐化模型中的组合安全。Lean 侧新增 `verified_package_semantics`：当 Bayer--Groth、跨密钥、OR、字节编码和状态认证组件安全与 refinement 保证成立时，完整包的公共有效性、residual-carrier 覆盖和槽位明文隶属关系由一个机器检查定理一次性导出。

## 1. 引言

设 canonical deck 为公开、无重复且按协议顺序固定的曲线点序列
`M=(m_0,...,m_{n-1})`。上一局结束时，玩家 `p` 的牌以 owner key `Q_p`
下的 residual carrier 保存。重建需要生成聚合公钥 `P=sum_p Q_p` 下的
下一局牌组，使得：

- 已持有的牌解密为 identity；
- 未持有的牌解密为原 canonical point；
- 持牌映射、分支和随机性不公开；
- 重建牌组可直接进入下一轮 shuffle。

核心难点是槽位语义。若只证明密文多重集或线性和正确，攻击者可用补偿密文让代数和成立而破坏单个槽位语义。逐槽 OR proof 把 `C_i` 的明文限制为 `0` 或 `-m_i`，跨密钥 proof 再把负分支连接到 owner-residual carrier，状态摘要则把 residual carrier 连接到真实历史发牌。

### 贡献

1. **聚合公钥统一。** 所有玩家贡献在同一 `P` 下加密，重建保持标准 ElGamal 密文形状。
2. **跨密钥负元证明。** 对 `R=Enc_Q(m;r)` 与 `S=Enc_P(-m;v)`，证明者只需知道 `(sk_Q,v)`，无需知道 `DL(R.c1)`。
3. **槽位语义 OR。** 每个 canonical slot 独立证明 `C_i in {Enc_P(0), Enc_P(-m_i)}`；分支和映射只在 witness 中。
4. **状态与 transcript 绑定。** context、epoch、prior state、公钥、canonical cards、residual carriers 和 contributions 全部进入域分离 transcript。
5. **组合 UC 模型。** 给出 `F_RECON`、real protocol、静态腐化模拟器和 ROM-hybrid 证明。
6. **机器检查组合层。** Lean 从组件保证导出完整包语义，不引入协议特定 axiom。

## 2. 相关工作

心智扑克通常使用可加密曲线点、re-encryption shuffle、部分解密和 DLEQ/Chaum--Pedersen 证明。Bayer--Groth 提供短的隐藏置换证明；Schnorr、Chaum--Pedersen 和 generalized-Schnorr 证明线性关系知识；Fiat--Shamir 在 ROM 中把交互 Sigma protocol 转成 NIZK；UC 框架要求把证明、状态、调度和并发调用放入同一理想功能。

Barnett--Smart [9] 给出后来广泛复用的 ElGamal mental-poker 基础和洗牌验证；Kurosawa 等人 [10] 与 Soo 等人 [11] 用 secret sharing 或可重排网络处理部分缺员/懒更新，但固定阈值与 coalition 恢复能力构成安全代价。较新的金融强制路线包括 Bentov 等人 [12]、Kaleidoscope [13] 和 ROYALE [14]；这些工作强化锁定、处罚和 UC 支付语义，但缺席处理主要通过 forfeit、超时或重新开局获得活性，而不是从认证 reveal-token 血统导出每个 residual carrier 的删除授权，也没有本文的逐槽 `0/-m_i` 语义。

与这些组件相比，本文的目标不是新的 shuffle argument，而是 reconstruction 特有的槽位语义绑定：shuffle 只隐藏映射，逐槽 OR 限制明文，跨密钥联合证明连接 residual carrier，状态摘要认证历史血统。这个分层使每个组件可以被独立实现和形式化，再由组合定理连接。

与 [7] 的对比需要区分活性与授权语义。先行工作解决 TTP-free dropout liveness；本文进一步把每个删除绑定到认证 singleton residual-carrier，并增加逐槽 `0/-m_i` OR proof、hidden carrier-to-slot map、exact coverage、多缺失密钥 residual 的保留策略，以及 Lean 机器检查的组合边界。

在更早期的 TTP-free 方案中，Barnett--Smart 路线要求离场者披露自己的秘密层，因此不能处理恶意或意外离场；基于 secret sharing 的路线虽能容忍固定数量缺员，但足够大的 coalition 可恢复全部牌面信息。相反，[7] 通过 CDS 部分知识证明和 veto 因子实现无需离场者配合的继续游戏，是本工作最接近的活性先行方案。

为了比较协议边界而不伪造运行数据，令 [7] 中活跃玩家数为 `N`，牌数为 `d=52`，历史发牌轮数为 `r`。其 dropout 后的重建需要重新生成整副牌：每个 face-down card 由 `N` 个 threshold-ElGamal 密文分量组成，公开牌组为 `dN` 个分量；每个玩家的 veto 层包含一组 `d` 个 re-masking pair、一个非 veto CDS 证明和 `r` 个 veto CDS 证明（每个均覆盖 `d` 个 Chaum--Pedersen 实例）；后续链式 re-masking 需要约 `dN^2` 个 Chaum--Pedersen 证明，再用 Barnett--Smart shuffle 证明处理 `dN` 个密文分量。作者完整论文 [8] 明确指出该 dropout 方案的效率仍需提升，且未给 dropout 路径的证明字节或运行时间实测。

| 属性 | Dropout-tolerant TTP-free Mental Poker [7] | 本文 |
|---|---|---|
| 离场处理 | 玩家退出后继续运行 | deadline 或 crash 后继续运行 |
| 离场后的牌组动作 | 从聚合公钥删除离场者份额并重建整副牌；其已抽牌回到牌组 | 只提交 state-bound reconstruction package；singleton owner-residual 精确移除，jointly keyed residual 保留 |
| 公开牌组规模 | 每张牌 `N` 个密文分量，共 `dN` | `d` 个 canonical contribution，另有 `k` 个认证 residual carrier |
| 证明关系规模 | 每玩家 `r+1` 个覆盖 `d` 实例的 CDS 证明；约 `dN^2` 个链式 CP 证明；再执行完整 shuffle proof | `k` 个跨密钥证明 + 1 个 Bayer--Groth + `d` 个槽位 OR |
| 移除授权 | 协议级 dropout 恢复 | 认证 singleton residual-carrier 血统 |
| 逐槽明文关系 | 未表述为零或负元隶属 | 每槽 `0/-m_i` OR proof |
| 映射隐私 | 由协议组件隐藏 | hidden carrier-to-slot map + Bayer--Groth |
| 多缺失密钥 | 未单列 carrier 类型 | jointly keyed residual 保留且不授权删除 |
| 可复现实测 | 仅符号协议描述；无 dropout 路径 runtime/proof bytes | native + WASM `d,k` 网格与 CSV；`d=52,k=13` bundle 27.75 KB |
| 形式化边界 | 论文密码学证明 | Lean 组合边界与显式假设 |

## 3. 模型与假设

设 `q` 为大素数，`F_q` 为标量域，`G` 为素数阶加法群，生成元为 `g`。对公钥 `P=xg`，

```text
Enc_P(m;r) = (rg, m+rP),   Dec_x(C)=C.c2-xC.c1.
```

ElGamal 同态性给出

```text
Enc_P(m;r)+Enc_P(m';r')=Enc_P(m+m';r+r').
```

`P=sum_p pk_p`，`Q_p=sk_p g`。canonical cards 非零且两两不同。

### 3.1 Reveal token 与 residual carrier 的推导

对槽位 `i`，完整聚合密文为

```text
C_i = Enc_P(m_i;r_i) = (r_i g, m_i+r_i P),
P = sum_p Q_p,  Q_p=sk_p g.
```

玩家 `p` 提交的 reveal token 为 `t_{p,i}=sk_p C_i.c1=r_i Q_p`，并附带
Chaum--Pedersen/DLEQ 证明，证明同一秘密标量同时连接 `Q_p=sk_p g` 与
`t_{p,i}=sk_p C_i.c1`。令 `A` 为已经提交有效 token 的玩家集合，
`U=Players\A` 为缺失 token 的玩家集合，`Q_U=sum_{p in U}Q_p`。从密文
第二分量减去所有已认证 token，得到

```text
R_i(A)
 = C_i - sum_{p in A}(0,t_{p,i})
 = (r_i g, m_i+r_i P-r_i sum_{p in A}Q_p)
 = (r_i g, m_i+r_i Q_U)
 = Enc_{Q_U}(m_i;r_i).
```

这一定义解释了为何一般对象应称为 residual carrier。当 `|U|=1`，设
`U={q}`，则 `Q_U=Q_q`，玩家 `q` 能用自己的私钥解密；这是当前实现的
owner-residual specialization。当 `|U|>=2`，`Q_U` 是多个公钥之和，任一
在线玩家都不拥有 `sk_U=sum_{p in U}sk_p`，因此无人单独知道原牌。尽管
如此，`R_i(A)` 仍是具有认证血统的合法 ElGamal 密文，协议可以在不公开
`m_i` 的情况下证明它与负贡献之间的群关系。`|U|=0` 则是完全揭示或重新
发牌边界，不应称为“可读牌”。

对隐藏映射 `i(j)`，重建贡献为 `S_j=Enc_P(-m_{i(j)};v_j)`，并证明

```text
Q_U=sk_U g,
S_j.c1=v_j g,
sk_U R_j.c1+v_j P=R_j.c2+S_j.c2.
```

单缺失 token 时，`sk_U` 就是 owner 私钥。多缺失 token 时，需要联合生成
或门限化的 aggregate-witness 证明接口；当前 AIR producer 尚未实现该路径。
一旦 carrier relation 成立，Bayer--Groth 隐藏 carrier-to-slot 映射，逐槽
OR proof 再把每个贡献限制为 `Enc_P(0)` 或 `Enc_P(-m_i)`，因此 reconstruction
的可靠性直接扎根于上述 token 减法推导，而非任何参与者预先知道明文。

### 假设

`A1` 曲线实现只接受 prime-order subgroup 的 canonical encoding，并正确实现群运算。

`A2` ElGamal 在 DDH 或等价假设下 IND-CPA 安全。

`A3` 每个 residual carrier 的隐藏随机性至少来自一次诚实、秘密、均匀的 shuffle rerandomizer；隐私使用平均情形 fresh-DLog 困难性。

`A4` Bayer--Groth 组件具有完备性、知识可靠性和零知识。

`A5` 跨密钥与槽位 OR Sigma protocol 具有特殊可靠性、完备性和 perfect HVZK；其 Fiat--Shamir 变换在 ROM 中安全。

`A6` 共享 transcript 的挑战重采样和顺序组合不引入跨组件攻击，域分离标签规范化。

`A7` `D_prev` 的认证状态功能不可伪造，Rust/AIR 字节编码与 Lean statement 精化一致。

`A8` 同一 epoch 的 residual-carrier sets 跨玩家不相交，每张 canonical card 至多一个 owner。

`A9` 静态腐化；被挑战牌的 owner secret 在执行结束前不泄露。

## 4. 协议

### 4.1 公共 statement

Statement 包含

```text
S=(context_digest, epoch, D_prev, P,Q,
   (m_i)_{i<n},(R_j)_{j<k},(C_i)_{i<n}).
```

实现保留线上 statement version 以便解码器 fail closed，但协议语义由上述字段决定。验证器拒绝长度不符、identity key/card/ciphertext、重复 canonical cards、`k=0` 或 `k>n`。

### 4.2 证明生成

玩家拥有 `sk_Q` 和 authenticated residual-carrier vector `R_0,...,R_{k-1}`。

1. 用 `sk_Q` 解密每个 `R_j`，要求明文在 canonical deck 中且互不重复。
2. 采样 `v_j`，构造 `S_j=Enc_P(-m_{i(j)};v_j)`；构造 `n-k` 个确定性零密文。
3. 用隐藏 permutation `pi` 和新鲜 rerandomizer `rho_i` 生成 canonical contributions。
4. 对每个 `R_j,S_j` 生成跨密钥联合证明。
5. 对 `(S||Z)` 到 `C` 生成 Bayer--Groth proof。
6. 对每个 canonical slot 生成 OR proof。

隐藏的 residual-carrier-to-slot 映射、分支、permutation 和随机性不出现在 wire proof 中。

### 4.3 跨密钥联合证明

对 `R=Enc_Q(m;r)` 与 `S=Enc_P(-m;v)`，证明知识 `(sk_Q,v)` 满足

```text
Q = sk_Q g
S.c1 = v g
sk_Q R.c1 + v P = R.c2 + S.c2.
```

这是 `G x G x G` 上的 two-scalar generalized-Schnorr relation。三条方程共享响应，不能由三个独立 Schnorr proof 拼接得到。由第三式可得两个密文明文和为零，因此负贡献确实对应 residual-carrier plaintext。见证不需要 `r=DL(R.c1)`。

### 4.4 槽位 OR proof

对槽 `i`，令 `T_0=C_i.c2`、`T_1=C_i.c2+m_i`。证明者证明存在 `v_i` 使

```text
C_i.c1=v_i g 且  T_b=v_i P
```

其中 `b=0` 表示零分支，`b=1` 表示负牌分支。使用标准 OR proof：真实 branch 诚实证明，另一 branch 用 challenge share 和 response 模拟，全局 challenge 满足 `e_0+e_1=e`。

### 4.5 聚合重建

宿主从 canonical base deck

```text
B_i=Enc_P(m_i;i+1)
```

开始，对 deadline 前通过验证的玩家求和：

```text
B~_i = B_i + sum_{p in S_submit} C_{p,i}.
```

未提交玩家是 no-op；超时影响 liveness，不允许提交者伪造他人的负贡献。在 `A8` 下，每个槽至多一个 negative branch。

### 4.6 证明系统设计取舍

协议刻意保留 Bayer--Groth 负责隐藏置换。它正是当前实现采用的成熟洗牌证明；用通用电路编译器替换它，改变的是 trusted-setup 边界和实现栈，而不是隔离本文新增的 reconstruction 语义。因此客户端构造由 Bayer--Groth、跨密钥 Sigma proof 和逐槽 OR proof 组成。

贡献在于语义组合，而非宣称单个证明引擎新颖：residual-carrier 血统、跨密钥负元关系、exact coverage 和逐槽零/负元语义。透明的 Sigma 代数便于映射到 Lean 组件接口，并使浏览器端证明保持在实测亚秒级范围内。代价是 proof 大于 succinct 聚合论证；host 侧聚合仍是未来工程方向，本文不将其用作未经实测的性能对比。

## 5. Correctness 与 Standalone Security

### 定理 1（完备性）

若 statement 满足认证状态条件，诚实玩家按 §4.2 生成 proof，则 verifier 接受，除去显式重采样的零挑战事件，概率界为 `O((n+k)q_H/q)`。

**证明。** 先证每个组件的 witness 确实存在。由 reveal-token lineage，
`R_j=Enc_Q(m_{i(j)};r_j)=(r_j g,m_{i(j)}+r_j Q)`。诚实证明者解密得到唯一的 canonical card `m_{i(j)}`，采样 `v_j` 后构造
`S_j=Enc_P(-m_{i(j)};v_j)=(v_j g,-m_{i(j)}+v_j P)`。代入跨密钥第三式：

```text
sk_Q R_j.c1 + v_j P
  = sk_Q(r_j g)+v_jP = r_jQ+v_jP,
R_j.c2+S_j.c2
  = (m_{i(j)}+r_jQ)+(-m_{i(j)}+v_jP)
  = r_jQ+v_jP.
```

因此三条跨密钥方程成立。对 `l=0,...,n-k-1`，确定性零贡献为
`Z_l=Enc_P(0;l+1)`。证明者按选定的单射 `i(j)` 构造 permutation，并给出每个输出槽的 rerandomizer；因此 `(S||Z)` 到 canonical contributions 的 Bayer--Groth witness 存在，A4 的完备性给出 shuffle proof 接受。

对槽位 `i`，若输入来自零贡献，则 `C_i.c1=v_i g` 且 `T_0=C_i.c2=v_i P`；若来自 `S_j`，则 `T_1=C_i.c2+m_{i(j)}=v_i P`。真实 branch 使用 `(v_i,commitment,response)` 诚实响应；模拟 branch 由选定的 challenge share 和 response 反向计算 commitment。两个 branch 的 challenge share 相加等于全局挑战，故 OR 验证方程成立。所有 statement 字段按相同 canonical 顺序进入 transcript，A6 保证不同组件的挑战互不混淆。

唯一非完备事件是某个 Fiat--Shamir 挑战或 challenge share 为零导致响应等式退化，或模拟点已被对手预先查询。`k` 个跨密钥证明与 `n` 个 OR proof 的并集界为 `O((n+k)q_H/q)`。□

### 定理 2（知识可靠性）

在 `A1,A4,A5,A6,A7` 下，对任意输出被接受 statement/proof 的 PPT adversary，存在 extractor 除误差外输出 witness `(removed,v,residualCarrierIndex,...)`，满足：

1. 每个槽 `C_i=Enc_P(0;v_i)` 或 `C_i=Enc_P(-m_i;v_i)`；
2. `removed_i=true` 当且仅当存在 residual carrier `j` 使 `residualCarrierIndex(j)=i`；
3. `residualCarrierIndex` 单射；
4. 每个 negative branch 对应 authenticated residual-carrier plaintext。

**证明。** 设 adversary 输出被 verifier 接受的 `(S,pi)`。对相同 statement 前缀 fork 到两个不同最终挑战。由 A6，前缀包含全部 statement 字段，因此两个 fork 使用同一 deck、carrier、contribution 和 transcript 状态。

第一，A4 的 Bayer--Groth 特殊可靠性从 accepting shuffle proof 提取 permutation `pi` 和 rerandomizers `rho`。这证明 statement.contributions 是负贡献向量、确定性零贡献向量和 `(pi,rho)` 作用后的结果；若提取失败，直接得到 BG extractor 的失败事件。

第二，对每个 `j`，跨密钥 Sigma proof 的两份 accepting transcript 提取同一 `(sk_Q,v_j)`。将 `sk_Q` 代入方程得
`S_j=Enc_P(-Dec_Q(R_j);v_j)`。A7/refinement 保证 `R_j` 来自 authenticated state，因此其明文被绑定到历史手牌；若攻击者提交不满足该血统的 carrier，则归约为状态摘要伪造或 serialization refinement 失败。

第三，对每个槽 `i`，OR proof 的两份 accepting transcript 提取 branch `b_i` 和 randomness `v_i`，并证明 `C_i` 的明文为 `0` 或 `-m_i`。与第一步提取的 permutation 合并，得到 `removed_i=true` 当且仅当某个已提取的 `R_j` 映射到槽 `i`。证明者在生成阶段先拒绝重复 residual plaintext，BG permutation 又是单射，所以 `residualCarrierIndex` 单射。任一提取失败计入 `eps_KS`；状态或字节映射失败计入 `eps_state+eps_ser`。□

### 定理 3（重建语义）

令 `chi_{p,i}=1` 当且仅当玩家 `p` 的 authenticated residual-carrier set 包含 `m_i`。在 `A8` 下：

```text
Dec_P(B~_i) =
  0,        若恰好一名玩家持有 m_i;
  m_i,      若没有玩家持有 m_i.
```

**证明。** 取一个提交者集合 `S_submit`，其证明均通过验证。对每个提交者应用定理 2。槽 `i` 的 contribution 明文属于 `{0,-m_i}`；只有当该提交者的某个 authenticated residual carrier 映射到 `i` 时才取负元。A8 保证跨玩家 residual-carrier 集不相交，因此同一 canonical card 至多收到一个负贡献。

对槽 `i` 求和：

```text
Dec_P(B~_i)
  = Dec_P(B_i + sum_{p in S_submit} C_{p,i})
  = m_i + sum_{p in S_submit} plaintext(C_{p,i}).
```

若存在授权 carrier，上式为 `m_i-m_i=0`；若不存在，所有项为零，上式为 `m_i`。对 `|U|>=2` 的 jointly keyed residual，当前协议不生成 owner-residual witness，也不把它放入 removal-authorizing vector，因此对应槽只可能收到零贡献，牌在新 deck 中保留且从不解密。□

## 6. UC 理想功能与组合安全

### 6.1 Hybrid 模型

协议运行在 `F_RO`、`F_STATE` 和已认证 key/shuffle/reveal functionality 的 hybrid 中。`F_STATE` 维护 canonical deck、公钥、上一局 assignment、residual-carrier lineage、epoch 和跨玩家不相交性。腐化集合静态固定，网络 adversary 可重排、丢弃和延迟消息。

### 6.2 `F_RECON`

`sid=(context,table,hand,epoch,D_prev)`。功能从 `F_STATE` 获得每个玩家的 authenticated residual-carrier plaintext set，但不把它发给 adversary。它等待每个玩家的 `SUBMIT` 或 deadline；令 `S` 为成功提交者，移除且仅移除 `S` 中玩家的 residual-carrier set。若 residual-carrier sets 重叠，输出 `STATE_INVALID`。

功能生成新的聚合加密牌组，只公开 `n,k,keys,epoch,D_prev`、验证结果、deadline/abort 状态和最终 state digest，不公开 owner-to-slot mapping、branch、随机性或 permutation。partial submission 建模为可用性事件：提交者可让自己的牌保留，但不能多删他人的牌。

### 6.3 Real protocol

Real protocol 从 `F_STATE` 获得 exact residual-carrier vector、`D_prev`、canonical deck 和 aggregate key；玩家运行 `ReconstructProof::prove`；verifier 独立验证后执行同态聚合；host 检查 ABI、call context、epoch、state digest 和下一轮 shuffle 输入。`ABORT` 产生 no-op 或 timeout，不产生任意 negative contribution。

### 6.4 条件 UC 定理

**定理 4。** 在 `A1--A9` 下，若 BG、跨密钥和 OR 的 FS-NIZK 版本在 `F_RO` 中可提取、可模拟且可并发组合，则任意静态腐化 adversary/environment 对 real protocol 和 `F_RECON` 的区分度不超过

```text
k*eps_DDH + eps_KS + eps_state + eps_ser
  + O((n+k)*q_H/q).
```

其中 `eps_KS` 是所有腐化提交的组件知识可靠性（分叉）误差之和，`eps_state`、`eps_ser` 分别是认证状态与序列化误差，`q_H` 是对手随机预言机查询次数上界。

**证明。** 证明由下面的模拟器构造、腐化提交提取和 `H0` 到 `H4` 的 hybrid 序列组成。

**模拟器。** `S` 在内部运行 adversary `A`，把随机预言机实现为惰性采样表加上有限个编程点，并连同 `A7` 下字节一致的编码一起转发 `F_RECON` 的公开输出：deck size、carrier 数、密钥、epoch、digest、验证与 deadline 状态。腐化集合静态固定，因此 `S` 预先知道哪些提交需要模拟、哪些需要提取。除贡献向量外的每个 statement 字段都是公开或来自状态：context、epoch、`D_prev`、密钥与 cards 在两个世界中相同；residual carriers（含全部 jointly keyed carriers）由认证先前状态固定，在两个世界中同分布，且重建过程中从不解密。

**诚实提交。** 对每个 owner-residual slot，模拟器抽取 `mu_j <- G`、`v_j <- Z_q`，令模拟负贡献 `S~_j=Enc_P(mu_j;v_j)`；确定性零贡献 `Z_l=Enc_P(0;l+1)` 与真实协议相同。随后抽取新鲜置换 `pi` 与 rerandomizer `rho`，把 canonical contributions 定义为重随机化洗牌 `C=[S~;Z]^(pi,rho)`。由构造存在完整 Bayer--Groth witness `(pi,rho)`，因此 `S` 直接运行诚实洗牌证明，不消耗 Bayer--Groth 的零知识性质。每个跨密钥证明由 HVZK 模拟产生：抽取 `z1,z2,e <- Z_q` 并计算承诺

```text
A1 = z1*g - e*Q
A2 = z2*g - e*S~_j.c1
A3 = z1*R_j.c1 + z2*P - e*(R_j.c2+S~_j.c2)
H(tau) := e
```

其中 `tau` 是 canonical transcript point；三条验证等式恒成立。每个逐槽 OR 证明由 CDS 模拟产生：取挑战份额 `e0,e1` 满足 `e0+e1=e`，同时模拟两个分支并编程共享挑战。`A6` 的域分离保证编程点唯一；若对手已查询过即将编程的点，`S` 中止，总代价至多 `(n+k)*q_H/q`。

**腐化提交。** `S` 原样转发对手 package bytes。被接受后，`S` 将 `A` 回卷到最后一个挑战，用新的编程挑战重放，并套用定理 2 的分叉提取器恢复置换、carrier 映射与全部分支 witness；提取失败受 `eps_KS` 约束。由定理 5，除非对手伪造状态摘要、组件证明或序列化 refinement（`eps_state+eps_ser`），提取出的负分支与认证 singleton missing-token derivation 完全一致；`S` 恰好将该集合提交给 `F_RECON`。未提交者在两个世界中都不产生消息；网络重排、丢弃与延迟经 deadline 语义转发。

**Hybrid 论证。** 设 `H0` 为真实执行。

1. `H0->H1`：用 `S` 的惰性表替换随机预言机。这是语法改动，两个视图相同。
2. `H1->H2`：把每个诚实跨密钥证明替换为上述 HVZK 模拟。联合 Sigma 协议完美 HVZK（`ReconstructionJointSigma.lean` 的 `sigma_perfect_hvzk` 机器检查），差异仅来自编程中止，至多 `k*q_H/q`。
3. `H2->H3`：把每个诚实逐槽 OR 证明替换为 CDS 模拟。OR 代数完美 HVZK（`ReconstructionSlotOr.lean` 的 `perfect_hvzk_algebraic`），附加代价至多 `n*q_H/q`。
4. `H3->H4`：逐个把诚实负贡献明文 `-m_i(j)` 替换为随机 `mu_j`，每个 carrier 一跳。每跳把一个 ElGamal 挑战密文嵌入模拟向量，派生 canonical contribution 是该密文的新鲜重随机化，因此每跳给出 DDH（A2）下的 IND-CPA 区分器；`k` 跳共 `k*eps_DDH`。canonical contributions 与诚实 Bayer--Groth 证明由构造直接跟随模拟向量。
5. `H4` 即与 `F_RECON` 和 `S` 的理想执行。各跳求和得到定理界；fresh-DLog 假设 `A3` 覆盖自上一轮继承的 jointly keyed carriers，它们在两个世界中同分布且从不被解密。

若只有 standalone NIZK，则结论限于同一 epoch 内固定顺序的一次调用。

### 6.5 非己手牌 veto

定义 `Veto(p,m)` 为玩家 `p` 的 accepted package 移除 `m`，但 `m` 不属于其 authenticated residual-carrier set。

**定理 5。** 在 `A1,A4,A5,A6,A7,A8,A9` 下，

```text
Pr[Veto(p,m)] <= eps_KS + eps_state + eps_ser.
```

若 package 被接受，定理 2 给出 negative branch 及对应 residual-carrier plaintext。`D_prev` 的 exact-vector binding 把该 residual carrier 识别为 `p` 的认证手牌；否则攻击者伪造 state digest、joint/OR/BG proof 或 serialization refinement。若 `p` 不提交，则不存在其贡献，不能产生他人 negative branch。若两个玩家 residual-carrier sets 重叠或 owner secret 泄露，该定理前提失效。

**证明。** 设 `Veto(p,m)` 发生但 `m` 不在 `p` 的 authenticated residual-carrier set 中。call context 和签名/会话绑定首先确定该 accepted package 归属于 `p`；若归属伪造，归约为认证失败。接受性允许对 package fork 并运行定理 2 的 extractor，得到某个 negative branch、其 randomness、carrier-to-slot 映射以及对应的 `R_j`。跨密钥可靠性给出 `R_j` 的明文为 `-plaintext(C_i)`；OR 可靠性给出 `plaintext(C_i)=-m`。因此 `R_j` 必须加密 `m`。

精确向量状态绑定要求 `D_prev` 中的 `(p,R_j,m)` 三元组存在且 epoch/missing-token set 匹配。若不存在，则攻击者完成下列事件之一：伪造 `D_prev`（`eps_state`）、伪造跨密钥/OR/BG 证明并使 extractor 失败（`eps_KS`）、或让 Rust/AIR 字节串映射到错误的 Lean statement（`eps_ser`）。三者并集即为定理界。若 `p` 未提交，其 proof package 不进入聚合，事件不可能由 `p` 的提交造成。若 residual sets 重叠或 owner secret 在执行结束前泄露，则前提 A8/A9 失效，定理不适用。□

## 7. Lean 形式化

Lean 项目使用固定 Mathlib/VCV-io revision 和 `autoImplicit=false`。主要模块为：

| 层 | 文件 | 代表定理 | 结论 |
|---|---|---|---|
| residual-carrier lineage | `ResidualCarrierProvenance.lean` | `authenticated_prior_hand_yields_residual carrier` | 认证 residual carrier 是 canonical plaintext 的 owner-key 密文 |
| 聚合语义 | `Reconstruction.lean` | `corrected_slot_semantics`, `aggregatePlaintext_unique_removal` | 逐槽重建正确性 |
| 跨密钥 Sigma | `ReconstructionJointSigma.lean` | `relation_iff_cross_key`, `sigma_speciallySound`, `sigma_perfect_hvzk` | 共享 `(sk_Q,v)` 的联合证明 |
| 槽位 OR | `ReconstructionSlotOr.lean` | `honest_accepts`, `specially_sound`, `perfect_hvzk_algebraic` | 完备、fork 提取与模拟 |
| 组合层 | `ReconstructionSecurity.lean` | `verified_package_semantics` | 组件保证蕴含完整包语义 |
| Veto 界 | `ReconstructionVeto.lean` | `veto_free_extraction`, `veto_error_bound_negligible` | 未授权槽位无法移除，误差并集可忽略 |

`ReconstructionSecurity.ComponentInterface` 汇集 BG、FS、transcript、serialization、state 和 disjointness 的安全保证。`VerifiedPackage` 同时保存 public statement、提取 witness、公共有效性和组件保证。`verified_package_semantics` 由该包一次性导出 `ValidRelation`、exact residual-carrier coverage 和逐槽 `{0,-m_i}` 隶属关系。

`scripts/count_sorries.sh` 报告 0 个 `sorry/admit`。`ReconstructionAxiomAudit.lean` 打印主要定理依赖的 Lean trusted axioms；reconstruction 模块不引入协议特定 axiom。

## 8. 实现与复现

代码分为 `poker-protocol-core`（曲线、ElGamal、transcript）、`poker-protocol-bg`（Bayer--Groth）、`poker-protocol-proofs`（reconstruction proof）、`poker_protocol`（ABI/native adapter）、`client-wasm`（浏览器桥接与 WASM 基准）和 `poker_protocol_lean`（形式化）。Native dispatch 当前使用 Stark curve/Poseidon 域；Ristretto wrapper 只构造 AIR/ABI submission，不在本仓库内验证 AIR archive。

复现命令：

```bash
cargo test --workspace
(cd poker_protocol_lean && lake build PokerProtocolLean)
(cd poker_protocol_lean && bash scripts/count_sorries.sh)
(cd client-wasm && wasm-pack test --node --release)
(cd client-wasm && wasm-pack build --target nodejs --release)
node client-wasm/benchmark.mjs 7 paper/experiments/reconstruction_wasm.csv
```

实测使用 StarkCurve、Poseidon-felt transcript、release 构建并取 7 次采样中位数。`n=52,k=13` 的 prove/verify 为 153.9/105.0 ms，proof 21.78 KB，prove peak 85.2 KiB；`k=26` 为 166.9/115.6 ms、24.69 KB、93.0 KiB。完整网格位于 `paper/experiments/reconstruction_stark.csv`，结果显示耗时、证明体积和峰值分配随 `n,k` 近似线性增长。

WASM 侧复用同一 `ReconstructProof` 与 production transcript，输出 `BrowserReconstructionV3Bundle` 后先 Borsh 解码再验证。release Node/V8、7 次采样中位下，`n=52,k=13` 的 prove/verify 为 646/471 ms，proof 21.78 KB，完整 bundle 27.75 KB；`k=26` 为 725/501 ms、24.69 KB、31.49 KB。完整网格位于 `paper/experiments/reconstruction_wasm.csv`。

## 9. 限制与未来工作

- 恶意不提交是 liveness 问题，需要 deadline、stake 或替代玩家机制。
- 状态认证不可省略；若 host 不认证 residual-carrier lineage，“非己手牌 veto”不成立。
- `n,k`、公钥、canonical cards、epoch 和 digest 公开；协议不隐藏牌组大小和 residual-carrier 数量。
- 完整 UC 依赖可组合 FS-NIZK；标准模型需要 CRS extractable NIZK 或新证明。
- 自适应腐化需要 erasure 或 non-committing 技术。
- 多重持有由跨玩家 disjointness invariant 强制。

## 10. 结论

该 reconstruction 协议把隐藏映射、跨密钥明文绑定、逐槽语义和状态/transcript 绑定组合成一个可审计证明系统。接受证明包意味着可提取 witness 满足 exact coverage 和槽位明文隶属关系；在状态血统和跨玩家不相交性成立时，不存在除安全误差外的非己手牌 veto。Lean 组合层把这些组件保证连接成单一机器检查定理，为条件 UC 结论提供了可复现的形式化边界。

## 参考文献

* R. Canetti. “Universally Composable Security: A New Paradigm for Cryptographic Protocols.” In IEEE FOCS, pp. 136–145, 2001. doi:10.1109/SFCS.2001.959888.
* S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” In EUROCRYPT, LNCS 7237, pp. 263–280, 2012. doi:10.1007/978-3-642-29011-4_17.
* D. Chaum and T. P. Pedersen. “Wallet Databases with Observers.” In CRYPTO, LNCS 740, pp. 89–105, 1992. doi:10.1007/3-540-48071-4_7.
* R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” In CRYPTO, LNCS 839, pp. 174–187, 1994. doi:10.1007/3-540-48658-5_19.
* A. Fiat and A. Shamir. “How To Prove Yourself: Practical Solutions to Identification and Signature Problems.” In CRYPTO, LNCS 263, pp. 186–194, 1986. doi:10.1007/3-540-47721-7_12.
* C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” In CRYPTO, LNCS 435, pp. 239–252, 1989. doi:10.1007/0-387-34805-0_22.
* J. Castellà-Roca, F. Sebé, and J. Domingo-Ferrer. “Dropout-Tolerant TTP-Free Mental Poker.” In Trust, Privacy, and Security in Digital Business, LNCS 3592, pp. 30–40, 2005. doi:10.1007/11537878_4.
* J. Castellà-Roca. “Contributions to Mental Poker.” PhD thesis, Universitat Autònoma de Barcelona, 2005.
* A. Barnett and N. P. Smart. “Mental Poker Revisited.” In Cryptography and Coding, LNCS 2898, pp. 370–383, 2003. doi:10.1007/978-3-540-40974-8_29.
* K. Kurosawa, Y. Katayama, and W. Ogata. “Reshufflable and Laziness Tolerant Mental Card Game Protocol.” IEICE Transactions on Fundamentals, 1997.
* W. H. Soo, A. Samsudin, and A. Goh. “Efficient Mental Card Shuffling via Optimised Arbitrary-Sized Benes Permutation Network.” In Information Security, LNCS 2433, pp. 446–458, 2002. doi:10.1007/3-540-45811-5_35.
* I. Bentov, R. Kumaresan, and A. Miller. “Instantaneous Decentralized Poker.” In ASIACRYPT, LNCS 10625, pp. 410–440, 2017. doi:10.1007/978-3-319-70697-9_15.
* B. David, R. Dowsley, and M. Larangeira. “Kaleidoscope: An Efficient Poker Protocol with Payment Distribution and Penalty Enforcement.” In Financial Cryptography and Data Security, LNCS 10958, pp. 500–519, 2018. doi:10.1007/978-3-662-58387-6_27.
* B. David, R. Dowsley, and M. Larangeira. “ROYALE: A Framework for Universally Composable Card Games with Financial Rewards and Penalties Enforcement.” In Financial Cryptography and Data Security, LNCS 11598, pp. 282–300, 2019. doi:10.1007/978-3-030-32101-7_18.

# 可组合的隐私保持牌组重建

## 槽位语义绑定、跨密钥联合证明与 Lean 形式化

**论文初稿**
日期：2026-09-16
代码基线：`poker-protocol-proofs` 的 `ReconstructProof`
开源仓库：[poker_protocol](https://github.com/linqining/poker_protocol)

> **主张边界。** 本文的条件 UC 定理在随机预言机、Bayer--Groth 组件安全、
> 状态认证和字节级 refinement 假设下成立。Lean 机器检查 readable lineage、
> 聚合语义、跨密钥 Sigma、槽位 OR，以及生产组件保证到完整 reconstruction
> 语义的组合定理。组件计算安全和序列化 refinement 是显式安全假设，不是
> 未完成的 Lean proof goal。

## 摘要

心智扑克需要在下一局开始前重建牌组：上一局被玩家持有的牌应从牌组中精确移除，其余牌仍保持可继续洗牌的 ElGamal 密文。普通 shuffle argument 只证明输出是输入的重加密置换，不能证明某个槽位的明文属于 `{0,-m_i}`。因此 reconstruction 需要把 shuffle 隐藏性、跨密钥明文绑定和逐槽语义放进同一个证明系统。

本文分析的协议让每个玩家在共同聚合公钥 `P` 下提交逐槽贡献

```text
C_i = Enc_P(0; v_i) 或 Enc_P(-m_i; v_i),
```

其中负分支只能由一个经过状态认证的 owner-readable card 支持。证明由四个部分组成：对每个 readable card 的跨密钥联合 generalized-Schnorr proof；隐藏 readable-to-slot 映射的 Bayer--Groth shuffle proof；每个 canonical slot 的二分支 OR proof；以及对上下文、epoch、状态摘要、公钥、牌点和全部密文的 transcript 绑定。

在明确假设下，我们证明接受的证明包可提取满足逐槽语义和 exact coverage 的见证；重建后的槽位为原牌或 identity；每张认证 readable card 至多且恰好移除一次；协议在 `F_RECON` 理想功能下满足静态腐化模型中的组合安全。Lean 侧新增 `verified_package_semantics`：当 Bayer--Groth、跨密钥、OR、字节编码和状态认证组件安全与 refinement 保证成立时，完整包的公共有效性、readable 覆盖和槽位明文隶属关系由一个机器检查定理一次性导出。

## 1. 引言

设 canonical deck 为公开、无重复且按协议顺序固定的曲线点序列
`M=(m_0,...,m_{n-1})`。上一局结束时，玩家 `p` 的牌以 owner key `Q_p`
下的 readable ciphertext 保存。重建需要生成聚合公钥 `P=sum_p Q_p` 下的
下一局牌组，使得：

- 已持有的牌解密为 identity；
- 未持有的牌解密为原 canonical point；
- 持牌映射、分支和随机性不公开；
- 重建牌组可直接进入下一轮 shuffle。

核心难点是槽位语义。若只证明密文多重集或线性和正确，攻击者可用补偿密文让代数和成立而破坏单个槽位语义。逐槽 OR proof 把 `C_i` 的明文限制为 `0` 或 `-m_i`，跨密钥 proof 再把负分支连接到 owner-readable card，状态摘要则把 readable card 连接到真实历史发牌。

### 贡献

1. **聚合公钥统一。** 所有玩家贡献在同一 `P` 下加密，重建保持标准 ElGamal 密文形状。
2. **跨密钥负元证明。** 对 `R=Enc_Q(m;r)` 与 `S=Enc_P(-m;v)`，证明者只需知道 `(sk_Q,v)`，无需知道 `DL(R.c1)`。
3. **槽位语义 OR。** 每个 canonical slot 独立证明 `C_i in {Enc_P(0), Enc_P(-m_i)}`；分支和映射只在 witness 中。
4. **状态与 transcript 绑定。** context、epoch、prior state、公钥、canonical cards、readable cards 和 contributions 全部进入域分离 transcript。
5. **组合 UC 模型。** 给出 `F_RECON`、real protocol、静态腐化模拟器和 ROM-hybrid 证明。
6. **机器检查组合层。** Lean 从组件保证导出完整包语义，不引入协议特定 axiom。

## 2. 相关工作

心智扑克通常使用可加密曲线点、re-encryption shuffle、部分解密和 DLEQ/Chaum--Pedersen 证明。Bayer--Groth 提供短的隐藏置换证明；Schnorr、Chaum--Pedersen 和 generalized-Schnorr 证明线性关系知识；Fiat--Shamir 在 ROM 中把交互 Sigma protocol 转成 NIZK；UC 框架要求把证明、状态、调度和并发调用放入同一理想功能。

与这些组件相比，本文的目标不是新的 shuffle argument，而是 reconstruction 特有的槽位语义绑定：shuffle 只隐藏映射，逐槽 OR 限制明文，跨密钥联合证明连接 readable ciphertext，状态摘要认证历史血统。这个分层使每个组件可以被独立实现和形式化，再由组合定理连接。

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

### 假设

`A1` 曲线实现只接受 prime-order subgroup 的 canonical encoding，并正确实现群运算。

`A2` ElGamal 在 DDH 或等价假设下 IND-CPA 安全。

`A3` 每个 readable card 的隐藏随机性至少来自一次诚实、秘密、均匀的 shuffle rerandomizer；隐私使用平均情形 fresh-DLog 困难性。

`A4` Bayer--Groth 组件具有完备性、知识可靠性和零知识。

`A5` 跨密钥与槽位 OR Sigma protocol 具有特殊可靠性、完备性和 perfect HVZK；其 Fiat--Shamir 变换在 ROM 中安全。

`A6` 共享 transcript 的挑战重采样和顺序组合不引入跨组件攻击，域分离标签规范化。

`A7` `D_prev` 的认证状态功能不可伪造，Rust/AIR 字节编码与 Lean statement 精化一致。

`A8` 同一 epoch 的 readable sets 跨玩家不相交，每张 canonical card 至多一个 owner。

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

玩家拥有 `sk_Q` 和 authenticated readable vector `R_0,...,R_{k-1}`。

1. 用 `sk_Q` 解密每个 `R_j`，要求明文在 canonical deck 中且互不重复。
2. 采样 `v_j`，构造 `S_j=Enc_P(-m_{i(j)};v_j)`；构造 `n-k` 个确定性零密文。
3. 用隐藏 permutation `pi` 和新鲜 rerandomizer `rho_i` 生成 canonical contributions。
4. 对每个 `R_j,S_j` 生成跨密钥联合证明。
5. 对 `(S||Z)` 到 `C` 生成 Bayer--Groth proof。
6. 对每个 canonical slot 生成 OR proof。

隐藏的 readable-to-slot 映射、分支、permutation 和随机性不出现在 wire proof 中。

### 4.3 跨密钥联合证明

对 `R=Enc_Q(m;r)` 与 `S=Enc_P(-m;v)`，证明知识 `(sk_Q,v)` 满足

```text
Q = sk_Q g
S.c1 = v g
sk_Q R.c1 + v P = R.c2 + S.c2.
```

这是 `G x G x G` 上的 two-scalar generalized-Schnorr relation。三条方程共享响应，不能由三个独立 Schnorr proof 拼接得到。由第三式可得两个密文明文和为零，因此负贡献确实对应 readable plaintext。见证不需要 `r=DL(R.c1)`。

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

## 5. Correctness 与 Standalone Security

### 定理 1（完备性）

若 statement 满足认证状态条件，诚实玩家按 §4.2 生成 proof，则 verifier 接受，除去显式重采样的零挑战事件，概率界为 `O((n+k)/q)`。

**证明。** readable lineage 给出 `R_j=Enc_Q(m_{i(j)};r_j)`；跨密钥方程直接代入成立。Bayer--Groth 对正确 permutation/rerandomizer 完备。OR proof 的真实 branch 诚实响应，模拟 branch 由定义满足验证式，challenge share 之和等于全局 challenge。所有 statement 字段按相同顺序进入 transcript。□

### 定理 2（知识可靠性）

在 `A1,A4,A5,A6,A7` 下，对任意输出被接受 statement/proof 的 PPT adversary，存在 extractor 除误差外输出 witness `(removed,v,readableIndex,...)`，满足：

1. 每个槽 `C_i=Enc_P(0;v_i)` 或 `C_i=Enc_P(-m_i;v_i)`；
2. `removed_i=true` 当且仅当存在 readable `j` 使 `readableIndex(j)=i`；
3. `readableIndex` 单射；
4. 每个 negative branch 对应 authenticated readable plaintext。

**证明。** 对共享 transcript fork。Bayer--Groth fork 提取 permutation/rerandomizer；跨密钥 proof 提取同一 `(sk_Q,v_j)`；OR fork 提取该槽 branch randomness。将提取对象代入 Lean relation 得 readable 方程和槽位方程，再由 exact coverage 得 2--4。任一失败给出对应组件安全或 refinement 归约。□

### 定理 3（重建语义）

令 `chi_{p,i}=1` 当且仅当玩家 `p` 的 authenticated readable set 包含 `m_i`。在 `A8` 下：

```text
Dec_P(B~_i) =
  0,        若恰好一名玩家持有 m_i;
  m_i,      若没有玩家持有 m_i.
```

**证明。** 由定理 2，每个贡献明文属于 `{0,-m_i}`；exact coverage 保证对应 readable 的槽得到负元。使用 ElGamal 同态性求和即可。□

## 6. UC 理想功能与组合安全

### 6.1 Hybrid 模型

协议运行在 `F_RO`、`F_STATE` 和已认证 key/shuffle/reveal functionality 的 hybrid 中。`F_STATE` 维护 canonical deck、公钥、上一局 assignment、readable lineage、epoch 和跨玩家不相交性。腐化集合静态固定，网络 adversary 可重排、丢弃和延迟消息。

### 6.2 `F_RECON`

`sid=(context,table,hand,epoch,D_prev)`。功能从 `F_STATE` 获得每个玩家的 authenticated readable plaintext set，但不把它发给 adversary。它等待每个玩家的 `SUBMIT` 或 deadline；令 `S` 为成功提交者，移除且仅移除 `S` 中玩家的 readable set。若 readable sets 重叠，输出 `STATE_INVALID`。

功能生成新的聚合加密牌组，只公开 `n,k,keys,epoch,D_prev`、验证结果、deadline/abort 状态和最终 state digest，不公开 owner-to-slot mapping、branch、随机性或 permutation。partial submission 建模为可用性事件：提交者可让自己的牌保留，但不能多删他人的牌。

### 6.3 Real protocol

Real protocol 从 `F_STATE` 获得 exact readable vector、`D_prev`、canonical deck 和 aggregate key；玩家运行 `ReconstructProof::prove`；verifier 独立验证后执行同态聚合；host 检查 ABI、call context、epoch、state digest 和下一轮 shuffle 输入。`ABORT` 产生 no-op 或 timeout，不产生任意 negative contribution。

### 6.4 条件 UC 定理

**定理 4。** 在 `A1--A9` 下，若 BG、跨密钥和 OR 的 FS-NIZK 版本在 `F_RO` 中可提取、可模拟且可并发组合，则任意静态腐化 adversary/environment 对 real protocol 和 `F_RECON` 的区分度不超过各组件 ZK/KS 误差、DDH/fresh-DLog、state 和 serialization 误差及 `O((n+k)/q)`。

模拟器对 corrupted proof 运行 extractor；对 honest proof 使用组件模拟器并按共享 transcript 编程 challenge；用 IND-CPA 和 fresh rerandomization hybrid 替换 honest contribution；对公开 ABI 字节逐字节转发。若恶意玩家尝试超出认证集合的负分支，归约到 state/proof/refinement 失败事件。由 UC composition theorem 得整体组合性；若只有 standalone NIZK，则结论限于同一 epoch 内固定顺序的一次调用。

### 6.5 非己手牌 veto

定义 `Veto(p,m)` 为玩家 `p` 的 accepted package 移除 `m`，但 `m` 不属于其 authenticated readable set。

**定理 5。** 在 `A1,A4,A5,A6,A7,A8` 下，

```text
Pr[Veto(p,m)] <= eps_KS + eps_state + eps_ser.
```

若 package 被接受，定理 2 给出 negative branch 及对应 readable plaintext。`D_prev` 的 exact-vector binding 把该 readable 识别为 `p` 的认证手牌；否则攻击者伪造 state digest、joint/OR/BG proof 或 serialization refinement。若 `p` 不提交，则不存在其贡献，不能产生他人 negative branch。若两个玩家 readable sets 重叠或 owner secret 泄露，该定理前提失效。

## 7. Lean 形式化

Lean 项目使用固定 Mathlib/VCV-io revision 和 `autoImplicit=false`。主要模块为：

| 层 | 文件 | 代表定理 | 结论 |
|---|---|---|---|
| readable lineage | `ReadableCardProvenance.lean` | `authenticated_prior_hand_yields_user_readable_card` | 认证 readable 是 canonical plaintext 的 owner-key 密文 |
| 聚合语义 | `Reconstruction.lean` | `corrected_slot_semantics`, `aggregatePlaintext_unique_removal` | 逐槽重建正确性 |
| 跨密钥 Sigma | `ReconstructionJointSigma.lean` | `relation_iff_cross_key`, `sigma_speciallySound`, `sigma_perfect_hvzk` | 共享 `(sk_Q,v)` 的联合证明 |
| 槽位 OR | `ReconstructionSlotOr.lean` | `honest_accepts`, `specially_sound`, `perfect_hvzk_algebraic` | 完备、fork 提取与模拟 |
| 组合层 | `ReconstructionSecurity.lean` | `verified_package_semantics` | 组件保证蕴含完整包语义 |

`ReconstructionSecurity.ComponentInterface` 汇集 BG、FS、transcript、serialization、state 和 disjointness 的安全保证。`VerifiedPackage` 同时保存 public statement、提取 witness、公共有效性和组件保证。`verified_package_semantics` 由该包一次性导出 `ValidRelation`、exact readable coverage 和逐槽 `{0,-m_i}` 隶属关系。

`scripts/count_sorries.sh` 报告 0 个 `sorry/admit`。`ReconstructionAxiomAudit.lean` 打印主要定理依赖的 Lean trusted axioms；reconstruction 模块不引入协议特定 axiom。

## 8. 实现与复现

代码分为 `poker-protocol-core`（曲线、ElGamal、transcript）、`poker-protocol-bg`（Bayer--Groth）、`poker-protocol-proofs`（reconstruction proof）、`poker_protocol`（ABI/native adapter）和 `poker_protocol_lean`（形式化）。Native dispatch 当前使用 Stark curve/Poseidon 域；Ristretto wrapper 只构造 AIR/ABI submission，不在本仓库内验证 AIR archive。

复现命令：

```bash
cargo test --workspace
cd poker_protocol_lean && lake build PokerProtocolLean
cd poker_protocol_lean && bash scripts/count_sorries.sh
```

实验报告应给出曲线、transcript、release/dev mode、proof bytes、prove/verify 时间、峰值内存，以及 `k` 个跨密钥证明和 `n` 个 OR proof 的线性增长。

## 9. 限制与未来工作

- 恶意不提交是 liveness 问题，需要 deadline、stake 或替代玩家机制。
- 状态认证不可省略；若 host 不认证 readable lineage，“非己手牌 veto”不成立。
- `n,k`、公钥、canonical cards、epoch 和 digest 公开；协议不隐藏牌组大小和 readable 数量。
- 完整 UC 依赖可组合 FS-NIZK；标准模型需要 CRS extractable NIZK 或新证明。
- 自适应腐化需要 erasure 或 non-committing 技术。
- 多重持有由跨玩家 disjointness invariant 强制。

## 10. 结论

该 reconstruction 协议把隐藏映射、跨密钥明文绑定、逐槽语义和状态/transcript 绑定组合成一个可审计证明系统。接受证明包意味着可提取 witness 满足 exact coverage 和槽位明文隶属关系；在状态血统和跨玩家不相交性成立时，不存在除安全误差外的非己手牌 veto。Lean 组合层把这些组件保证连接成单一机器检查定理，为条件 UC 结论提供了可复现的形式化边界。

## 参考文献

* R. Canetti. “Universally Composable Security.” FOCS 2001.
* S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” EUROCRYPT 2012.
* D. Chaum and T. Pedersen. “Wallet Databases with Observers.” CRYPTO 1992.
* R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” CRYPTO 1994.
* A. Fiat and A. Shamir. “How to Prove Yourself.” CRYPTO 1986.
* C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” CRYPTO 1989.

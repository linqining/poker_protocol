# 可组合的隐私保持牌组重建

## 具有槽位语义绑定的 Bayer–Groth、跨密钥联合证明与 Lean 形式化

**论文初稿（面向密码学理论/系统顶级期刊）**  
版本：2026-09-16  
代码基线：`poker-protocol-proofs` 的 `ReconstructProofV3`  
开源仓库：[https://github.com/linqining/poker_protocol](https://github.com/linqining/poker_protocol)

> **主张边界。** 本稿把“完整 Rust 实现安全”写成一个在随机预言机、
> Bayer–Groth 组件安全、状态认证和字节级 refinement 假设下的条件 UC 定理。
> Lean 已经机器检查代数关系、牌面血统、联合 Σ 协议和槽位 OR 协议；它还没有
> 形式化整个 Bayer–Groth Rust 实现、共享 Fiat–Shamir transcript 或生产状态机。
> 因而本文不声称生产 binary 已被无条件验证。

## 摘要

心智扑克需要在不公开私牌的情况下重建牌组：上一手由玩家持有的牌必须从下一手牌组中精确移除，而其余牌的密文应保持可继续洗牌。我们研究了一个现有的 reconstruction 实现，并发现旧版（V2）同时存在三类结构性问题：错位交换可在有序密文关系下通过验证、公开幂随机性泄露零/非零分支，以及不同玩家公钥下的密文不能被当作同一聚合公钥下的密文相加。

本文提出并形式化分析 V3。每个玩家在共同聚合公钥下提交逐槽贡献

\[
 C_i=\operatorname{Enc}_{P}(0;v_i)\quad\text{或}\quad
 C_i=\operatorname{Enc}_{P}(-m_i;v_i),
\]

其中第二个分支只能由一个经过状态认证的 owner-readable card 支持。实现由四个互补组件组成：(i) 对每个 readable card 的跨密钥联合 generalized-Schnorr 证明；(ii) Bayer–Groth 隐藏置换/重随机化证明；(iii) 每个 canonical slot 上的二分支 Chaum–Pedersen OR 证明；(iv) 将上下文、epoch、先前状态摘要、公钥、牌点和密文完整吸收到 transcript 的状态绑定。与仅证明多重集相等的 shuffle argument 不同，槽位 OR 证明提供了“该槽只能是零或该槽牌的负元”的语义绑定，因此排除了 V2 的 misplaced-swap 攻击。

在明确列出的 ROM、知识可靠性、ElGamal 隐藏性、Bayer–Groth 安全性、状态血统和序列化 refinement 假设下，我们证明：接受的 V3 包产生一个可提取见证；重建后的槽位恰为原牌或 identity，且每张认证 readable card 至多且恰好移除一次；协议在 `F_RECON` 理想功能下满足静态腐化模型中的组合安全。论文同时给出一个“非己手牌 veto”定理：若 state digest 认证 owner-readable 集合且跨玩家集合不相交，恶意玩家使非己手牌被移除的概率至多为安全误差之和；若缺少这些状态不变量，该结论不能由 reconstruction proof 单独推出。

项目中的 Lean 4 开发包含零 `sorry`/`admit` 的 V2 反例、V3 代数语义、联合 Σ/OR 证明和牌面血统定理。我们精确区分机器检查的内容与仍需假设的生产链接层，为形式化验证在密码协议论文中的可复现使用提供一个可审计边界。

## 1. 引言

### 1.1 问题

设 canonical deck 为公开且无重复的曲线点序列
`M=(m_0,…,m_{n-1})`。每一轮结束时，玩家 `p` 持有的牌以 owner key
`Q_p` 下的 ElGamal 密文保存。下一轮需要生成聚合公钥
`P=\sum_p Q_p` 下的牌组，使得：

* 持有过的牌解密为 identity（空槽）；
* 未持有的牌仍解密为原来的 canonical point；
* 谁持有哪一槽、哪些槽被移除以及重建时使用的随机性不被公开；
* 重建后的密文可以直接进入下一次 shuffle。

这不是普通的 shuffle：shuffle 只证明输出是输入的重加密置换，而 reconstruction 还必须证明每个输出槽的**语义**。一个仅有 Bayer–Groth 证明的方案无法阻止“把牌 A 的负元放入牌 B 的槽位，再用一个补偿项让和看起来正确”的攻击。

### 1.2 贡献

本文的实现与证明贡献如下。

1. **聚合公钥统一。** 所有玩家贡献均在同一个 `P` 下加密，消除了 V2 的跨密钥聚合形状错误。
2. **跨密钥负元证明。** 对 `R=Enc_Q(m;r)` 与 `S=Enc_P(-m;v)`，证明者只需知道 `(sk_Q,v)`，无需知道 `DL(R.c1)`，并用一个共享见证的三方线性关系绑定两把公钥和两个密文。
3. **槽位语义 OR。** 每个 canonical slot 单独证明 `C_i∈{Enc_P(0),Enc_P(-m_i)}`。分支和 readable-to-slot 映射只存在于 witness，不出现在 wire proof 中。
4. **状态与 transcript 绑定。** `context_digest`、单调 `reconstruction_epoch`、`prior_state_digest`、双方公钥、canonical cards、readable cards 和 contributions 全部进入域分离 transcript。
5. **可组合安全模型。** 我们给出 `F_RECON`、real protocol、静态腐化模拟器和 ROM-hybrid UC 证明，并给出仅在 standalone NIZK 假设下仍成立的 sequential-composition 版本。
6. **机器检查边界。** Lean 证明 V2 反例、V3 关系完备性和语义、联合 Σ/OR 协议及 readable-card lineage；Bayer–Groth、FS 共享 transcript、Rust↔Lean 序列化和状态机链接义务被显式作为假设。

### 1.3 结论应如何理解

V3 不是“任何调用者都能任意 veto 某张牌”的接口。一个合法的负贡献必须同时满足：它来自 authenticated readable card、其 plaintext 与 canonical slot 相同、并且贡献在聚合公钥下是该 plaintext 的负元。若调用者没有该槽对应的 owner-readable card，或者 state digest 没有把该 card 绑定给该调用者，证明应拒绝。唯一的例外是调用者选择不提交或超时；这是 liveness/availability 行为，不能伪造为另一玩家的合法移除。

## 2. 相关工作与设计对比

心智扑克协议通常把牌编码为可加密曲线点，并通过 re-encryption shuffle、部分解密或 DLEQ/Chaum–Pedersen 证明实现隐私。Bayer–Groth shuffle argument 给出短的隐藏置换证明；Schnorr、Chaum–Pedersen 和 generalized-Schnorr 提供线性关系的知识证明；Fiat–Shamir 在 ROM 中将交互协议转为 NIZK。UC 框架则要求把这些证明与状态、网络调度和并发调用放进同一理想功能，而不能把 standalone “验证通过”直接等同于 UC。

本项目的 V2 reconstruction 延续了“swap-out 密文 + 有序加密关系”的思路，但该关系只约束

\[
 O_i+P_i=\operatorname{Enc}_{Q}(m_i),
\]

而不约束 `P_i` 的 plaintext。V3 的差异在于把“贡献的 plaintext membership”作为独立证明目标，并把跨密钥关联放入一个共享 witness 的关系；这也是本文相对于先前 veto/重建思路的核心创新。V2 保留为兼容类型和反例靶，不作为任何安全定理的基础。

### 2.1 与 2005 年 dropout-tolerant veto 协议的关系

本文同时分析的 Castellà-Roca–Sebé–Domingo-Ferrer 方案（TrustBus 2005）采用乘法群中的牌值、阈值 ElGamal 指数和 Chaum–Pedersen 证明；玩家用自己曾经知道的指数 `τ` 构造“不满足可解密关系”的重掩码因子，从而否决已抽到的牌。该方案的引理 3 正是“非己牌不可否决”的来源：伪造一个旧轮次的否决关系需要知道该轮的离散对数。它不是本文 V3 的实现，也没有给出现代 UC/组合安全证明。

V3 采用加法曲线群、统一聚合公钥下的 ElGamal 密文和固定 canonical slot。V3 的负贡献不是原论文的“不满足解密关系”的重掩码，而是显式的 `Enc_P(-m)`，并通过跨密钥联合证明绑定到 owner-readable ciphertext，再通过逐槽 OR 证明绑定到唯一 canonical card。因而两者的“veto”语义不同：原协议让牌在后续开牌时不可解密，V3 让牌在同态重建后变为 identity。原协议的 dropout 处理是移除离场玩家的公钥份额，使其旧牌恢复可用；V3 的 no-op/abort 则由 `F_RECON` 的提交截止时间建模。本文不把两种机制混称，也不把原协议的证明自动迁移到 V3。

## 3. 模型、记号与安全假设

### 3.1 代数设置

设 `q` 为大素数，`F_q` 为标量域，`G` 为素数阶 `q` 的加法群，生成元为 `g`。曲线点既作为群元素也作为可加消息。对公钥 `P=xg`，定义

\[
 \operatorname{Enc}_{P}(m;r)=(rg,\;m+rP),
 \qquad
 \operatorname{Dec}_{x}(C)=C.c_2-xC.c_1.
\]

密文相加满足

\[
 \operatorname{Enc}_{P}(m;r)+\operatorname{Enc}_{P}(m';r')
 =\operatorname{Enc}_{P}(m+m';r+r').
\]

canonical cards `m_i` 非 identity 且两两不同；`P=\sum_{p∈\mathcal P}pk_p` 为聚合公钥，`Q_p=sk_p g` 为玩家公钥。

### 3.2 认证状态

状态摘要 `D_prev` 认证如下对象：

* canonical `init_deck` 的 card points 及顺序；
* 每一轮 mask/remask 和 shuffle 的验证结果；
* 发牌位置与 owner；
* 所有非 owner 的有效 reveal token，以及 token 绑定的 dealt ciphertext；
* 玩家 `p` 的 exact readable vector `R_p`；
* 同一 epoch 中不同玩家 readable 集合不相交。

因此，`R=Enc_{Q_p}(m;r)` 不是调用者自由选择的输入。它有一条从 `init_deck` 到 prior hand 再到 owner-readable ciphertext 的认证 lineage。

### 3.3 假设

本文把下列条件命名为 `A_1`–`A_9`。

* `A_1`：曲线实现只接受 prime-order subgroup 中的 canonical encoding，并正确实现群运算。
* `A_2`：ElGamal 在 DDH（或等价的选择明文隐藏）假设下满足 IND-CPA。
* `A_3`：对 readable card 的 `c1=r g`，至少一次诚实、秘密、均匀的 shuffle rerandomizer 存在。隐私使用平均意义 fresh-DLog hardness，而不是“每个点的离散对数都困难”（后者因 `DL_g(g)=1` 而为假）。
* `A_4`：Bayer–Groth 实现具有完备性、知识可靠性和 ZK；其 commitment key、挑战和重随机化满足标准参数条件。
* `A_5`：joint generalized-Schnorr 与 slot OR 在 FS/ROM 下具有可提取知识可靠性和可模拟 ZK。
* `A_6`：FS challenge 的零值重采样和 sequential transcript 组合不会引入跨组件攻击；域分离标签是规范化的。
* `A_7`：`D_prev` 的 authenticated-state 功能不可伪造，且 Rust/AIR 的字节编码精确对应 Lean statement。
* `A_8`：同一 epoch 的 readable sets 跨玩家不相交、每张 canonical card 最多被一个 owner 持有。
* `A_9`：静态腐化；被挑战牌的 owner secret 在执行结束前不泄露。自适应腐化需要额外的 erasure/non-committing 假设，本文不宣称已覆盖。

## 4. V3 协议

### 4.1 公共 statement

`Statement` 包含

\[
 S=(v,ctx,epoch,D_{prev},P,Q,
      (m_i)_{i<n},(R_j)_{j<k},(C_i)_{i<n}).
\]

实现中的 `version=3`、`context_digest`、`reconstruction_epoch` 和 `prior_state_digest` 进入 transcript。验证器 fail-closed 地拒绝：长度不符、identity key/card/ciphertext、重复 canonical cards、`k=0` 或 `k>n`。

### 4.2 证明生成

玩家 `p` 拥有 `sk_Q` 和 readable vector `R_0,…,R_{k-1}`。

1. 用 `sk_Q` 解密每个 `R_j` 得到 `m_{ι(j)}`，检查 plaintext 在 canonical deck 中且互不重复。
2. 采样新随机性 `v_j`，构造
   `S_j=Enc_P(-m_{ι(j)};v_j)`；再构造 `n-k` 个确定性零密文 `Z_l=Enc_P(0;l+1)`。
3. 用隐藏 permutation `π` 和新鲜 rerandomizer `ρ_i` 生成 canonical contributions
   `C_i=ReEnc_P((S\|Z)_{π(i)};ρ_i)`。
4. 对每个 `j` 生成跨密钥联合证明（见 §4.3）。
5. 对 `(S\|Z)` 到 `C` 生成 Bayer–Groth proof。
6. 对每个 canonical slot `i` 生成 slot OR proof（见 §4.4）。

隐藏的 `ι`、`π`、分支 bit 和所有随机性不出现在 wire proof 中。

### 4.3 跨密钥联合证明

对 `R=Enc_Q(m;r)` 和 `S=Enc_P(-m;v)`，证明知识 `(sk_Q,v)` 满足

\[
 Q=sk_Qg,\qquad S.c_1=vg,\qquad
 sk_QR.c_1+vP=R.c_2+S.c_2. \tag{1}
\]

这是一个在 `G×G×G` 上的 two-scalar generalized-Schnorr relation。第三条方程与前两条共享同一 response，不能被三个相互独立的 Schnorr proof 拼接替代。由 (1)：

\[
 (R.c_2-sk_QR.c_1)+(S.c_2-vP)=0,
\]

故两个密文 plaintext 互为相反数。注意证明 witness 不含 `r=DL_g(R.c_1)`；未知 `r` 是隐私要求，而不是 soundness 要求。

### 4.4 槽位 OR 证明

对每个槽 `i`，令 `T_0=C_i.c_2`、`T_1=C_i.c_2+m_i`。证明者证明存在 `v_i` 使

\[
 C_i.c_1=v_i g\ \land\ T_b=v_iP
\]

其中 `b=0` 表示 `C_i=Enc_P(0;v_i)`，`b=1` 表示 `C_i=Enc_P(-m_i;v_i)`。使用标准 Chaum–Pedersen OR：一个 branch 真实证明，另一个 branch 用 challenge share 和 response 模拟；全局 challenge 满足 `e_0+e_1=e`。wire transcript 只有两组 commitments/challenges/responses，不包含 `b`。

### 4.5 聚合重建

宿主从 canonical base deck

\[
 B_i=Enc_P(m_i;i+1)
\]

开始，对所有在 deadline 前提交且通过验证的玩家求和：

\[
 \widetilde B_i=B_i+\sum_{p\in S_{submit}}C_{p,i}. \tag{2}
\]

没有提交的玩家是 no-op；该策略保证超时只影响可用性，不允许提交者伪造他人的负贡献。若状态机保证 `A_8`，每个槽至多出现一个 negative branch。

## 5. 正确性与 standalone 安全定理

### 定理 1（完备性）

若 statement 满足认证状态条件，诚实玩家按 §4.2 生成 proof，则 V3 verifier 接受，除去显式拒绝 identity/zero challenge 的重采样事件。该事件概率至多为 `O((n+k)/q)`。

**证明。** readable lineage 给出 `R_j=Enc_Q(m_{ι(j)};r_j)`；由式 (1) 的直接代入得到 cross-key commitments 的验证等式。Bayer–Groth 在正确 permutation/rerandomizer 下完备。对每个 slot，真实 branch 使用 `v_i`，另一 branch 按模拟公式构造，且两份 challenge share 之和等于全局 challenge；因此 slot OR 接受。statement 的所有字段按相同顺序进入 transcript，故 prover/verifier challenge 一致。□

### 定理 2（V3 关系的知识可靠性）

在 `A_1,A_4,A_5,A_6,A_7` 下，任意 PPT adversary 输出一个被接受的 statement/proof，存在 ROM extractor `Ext`，除以

\[
 \epsilon_{KS}=\epsilon_{BG}^{KS}+
 k\varepsilon_{Joint}^{KS}+n\varepsilon_{OR}^{KS}+\varepsilon_{FS}+\varepsilon_{refine}
\]

之外，输出 witness `(removed,v,readableIndex,…)` 满足：

1. 对每个 `i`，`C_i=Enc_P(0;v_i)` 或 `C_i=Enc_P(-m_i;v_i)`；
2. `removed_i=true` 当且仅当存在唯一 readable index `j` 使 `readableIndex(j)=i`；
3. `readableIndex` 单射；
4. 每个 negative branch 与 authenticated readable card 的 plaintext 相反。

**证明。** 对共享 transcript 编程并 fork。对 Bayer–Groth fork 提取 permutation/rerandomizer witness；对每个 joint proof 的两个不同 challenge 提取同一 `(sk_Q,v_j)`；对每个 slot OR 的两个不同全局 challenge，至少一条 branch share 改变，从而提取该 branch 的 randomness。Lean 定理 `specially_sound` 形式化了最后一步。将提取 witness 代入 `CrossKeyNegationRelation`，由式 (1) 得到负元 plaintext；将 slot relation 与 BG permutation 合取，得到 1–4。若任一步失败，则给出相应组件的 soundness/FS/refinement 归约。□

### 定理 3（重建语义）

设 `χ_{p,i}=1` 当且仅当玩家 `p` 的 authenticated readable set 包含 `m_i`。在 `A_8` 下：

\[
 Dec_P(\widetilde B_i)=
 \begin{cases}
  0,&\sum_pχ_{p,i}=1,\\
  m_i,&\sum_pχ_{p,i}=0.
 \end{cases} \tag{3}
\]

若状态允许重复 owner，则式 (3) 不应被声称：两个合法 negative branch 会产生 `-m_i`。这是为何跨玩家 disjointness 属于安全 TCB，而不是单个 reconstruction proof 可以独立证明的事实。

**证明。** 由定理 2，每个贡献 plaintext 属于 `{0,-m_i}`；由精确 coverage，恰有对应 readable 的槽得到负元。对式 (2) 使用 ElGamal 同态性即可。Lean 中对应 `corrected_slot_semantics`、`aggregatePlaintext_no_removal` 和 `aggregatePlaintext_unique_removal`。□

## 6. V2 反例与 V3 修复

### 6.1 Misplaced swap

V2 只检查 `O_i+P_i=Enc_Q(m_i)`。取两个不同非零牌点 `A≠B`：

\[
 P_i=Enc_Q(A;s),\qquad O_i=Enc_Q(B-A;r).
\]

则 `O_i+P_i=Enc_Q(B;r+s)`，验证通过，但 `B-A` 既不是零也不是 `B`。该攻击只使用公开群减法，不需要求解离散对数。V3 的 slot OR 强制 `P_i` 的 plaintext 只能是 `0` 或 `-m_i`，故攻击者无法构造这个 witness。

### 6.2 公开随机性泄露分支

V2 使用公开 `s_i=coefficient^{i+1}`。观察者可计算

\[
 O_i.c_2-s_iQ,
\]

直接区分 identity 与 `m_i`，从而知道被移除槽位。V3 的 `v_i`、BG rerandomizer 和 OR response 均为隐藏随机量；canonical base deck 的 `i+1` 只用于公开 card point，不承担 private contribution 的随机性。

### 6.3 跨密钥聚合错误

若 `C_1=Enc_{Q_1}(m_1;r)` 与 `C_2=Enc_{Q_2}(m_2;r)` 被相加，第一分量为 `2rg`，但 key term 为 `r(Q_1+Q_2)`；这一般不是某个单一 aggregate-key ElGamal 密文。V3 从生成阶段就统一使用 `P`，因此式 (2) 保持标准密文形状。

## 7. UC 理想功能与组合安全

### 7.1 混合模型

我们在 `\mathcal F_{RO}`、`\mathcal F_{STATE}` 和已认证 key/shuffle/reveal functionality 的 hybrid 中定义协议。`\mathcal F_{RO}` 为可编程随机预言机；`\mathcal F_{STATE}` 维护 canonical deck、玩家公钥、prior-hand assignment、readable lineage、epoch 和跨玩家不相交性。腐化集合 `C` 静态固定，网络 adversary 可重排、丢弃和延迟消息。

### 7.2 理想功能 `F_RECON`

`F_RECON` 的 session identifier 为
`sid=(context,table,hand,epoch,D_prev)`。它执行：

1. 从 `F_STATE` 接收 `(M,\{U_p\}_{p∈P})`，其中 `M=(m_i)` 是 canonical deck，`U_p` 是 p 的 authenticated readable plaintext set；功能不会把 `U_p` 发给 adversary。
2. 等待每个玩家的 `SUBMIT` 或 deadline。对 honest player，`SUBMIT` 由其私有端口隐式触发；对 corrupted player，adversary 可选择 `SUBMIT` 或 `ABORT`。
3. 令 `S` 为在 deadline 前成功提交的玩家。若 `p∈S`，移除 `U_p`；若 `p∉S`，不移除 `U_p`。若 `U_p` 与其他集合重叠，功能向 `F_STATE` 报告 `STATE_INVALID`，而不是默默执行双重负贡献。
4. 生成新的聚合加密牌组，只向公共端口泄露 `n,k,keys,epoch,D_prev`、验证结果、deadline/abort 状态和最终 state digest；不泄露 owner-to-slot mapping、branch bit、ElGamal randomness 或 permutation。
5. 向 state port 输出 `REBUILT` 或 `ABORTED`。对网络 adversary 可见的密文分布与 real protocol 相同；其 plaintext 只按上述语义取 `m_i` 或 identity。

该功能明确建模 partial submission：它保证安全性（恶意玩家不能多删牌），但不保证 liveness（恶意玩家可以不提交）。若应用需要强制重建，必须在功能中加入 stake/slashing/替代 player，而不是把它误写成密码学 soundness。

### 7.3 Real protocol `Π_RECON`

论文所分析的 real protocol 由以下步骤组成：

* 从 `F_STATE`/host 获得 exact `R_p`、`D_prev`、`M` 和 `P`；
* 玩家运行 `ReconstructProofV3::prove`，发送 statement/proof；
* verifier 运行 V3，成功后运行式 (2) 的 homomorphic aggregation；
* host/AIR 检查 request ABI、call context、epoch、state digest 和下一轮 shuffle 输入。

`ABORT` 只产生 no-op 或 timeout，不产生任意 negative contribution。

当前仓库已经实现 V3 prover/verifier、Borsh ABI 和 native precompile adapter，客户端也能构造可验证的 `ReconstructDeckV3`；但 `z_poker/protocol/game.rs` 尚未把 V3 的 prior-state exact-vector 检查、跨玩家 disjointness 和聚合状态转移完整接成一个端到端生产状态机。因此，本节的 `Π_RECON` 是对“代码核心 + 必须补齐的宿主链接层”的精确定义，而不是声称现有 game runtime 已完整实现该 real protocol。

### 7.4 条件 UC 定理

**定理 4（V3 的 ROM-hybrid UC realization，条件形式）。** 假设 `A_1`–`A_9`，并进一步假设 BG、joint proof 和 slot OR 的 FS-NIZK 版本在 `\mathcal F_{RO}` 中具有可提取、可模拟且可并发组合的安全性，则对于任意静态腐化 PPT adversary `A` 和环境 `Z`，存在 PPT simulator `S` 使

\[
 \left|\Pr[\mathsf{Exec}_{\Pi_{RECON},A,Z}=1]
      -\Pr[\mathsf{Exec}_{F_{RECON},S,Z}=1]\right|
 \leq \varepsilon_{UC},
\]

其中

\[
\begin{aligned}
\varepsilon_{UC}\leq{}&
 \varepsilon_{BG}^{ZK}+\varepsilon_{BG}^{KS}
 +k\varepsilon_{Joint}^{ZK/KS}
 +n\varepsilon_{OR}^{ZK/KS}\\
 &+\varepsilon_{FS}^{shared-ROM}
 +\varepsilon_{DDH}
 +\varepsilon_{freshDLog}
 +\varepsilon_{state}
 +\varepsilon_{ser}+O((n+k)/q).
\end{aligned}
\]

`ε_state` 包括 prior-state 伪造、跨玩家重复和 epoch replay；`ε_ser` 包括 Rust/AIR 与 Lean statement/transcript 不一致。

#### 模拟器

模拟器 `S` 从 `F_RECON` 得到 public metadata、每个 corrupted player 的 submit/abort 和最终抽象 state。它执行：

1. 对 corrupted proof，运行 extractor；若 extractor 得不到满足 V3 relation 的 witness，输出 `FAIL`，该事件归约到知识可靠性误差。
2. 对 honest player 的 joint/OR/BG proof，使用各组件的 ROM simulator 生成 transcript；按共享 transcript 顺序编程 challenge，所有外层 statement 字段保持真实值。
3. 对 honest contribution ciphertext，使用 IND-CPA hybrid 将真实 plaintext branch 替换为 `0/-m_i` 的理想语义，并使用 fresh rerandomization 复现密文分布。`freshDLog` 保证 readable ciphertext 不泄露 card plaintext。
4. 将 extracted corrupted contributions 和 ideal `U_p` 交给 `F_RECON` 的状态检查。若恶意玩家尝试超出其认证集合的 negative branch，模拟器使 state/verification 失败，并将事件归约到 `ε_state+ε_KS`。
5. 对公开 ABI/序列化字段逐字节转发；任一不一致都归约到 `ε_ser`。

#### Hybrid 证明

* `H_0`：真实执行。
* `H_1`：逐个替换 honest BG proof；差异由 `ε_BG^{ZK}` 给出。
* `H_2`：逐个替换 honest joint/OR proof；差异由 `kε_{Joint}^{ZK}+nε_{OR}^{ZK}` 给出。
* `H_3`：对所有 accepted corrupted packages 运行 ROM extractor；若关系失败，则得到 `ε_BG^{KS}+kε_{Joint}^{KS}+nε_{OR}^{KS}+ε_FS` 的归约。
* `H_4`：把 authenticated state 和 prior digest 替换为 `F_STATE`；差异为 `ε_state+ε_ser`。
* `H_5`：用理想功能的 fresh ciphertext 与 no-op/negative 语义替换 honest contributions；差异为 `ε_DDH+ε_freshDLog`，零挑战 resampling 加 `O((n+k)/q)`。
* `H_6` 的公共输出、abort 行为和最终 digest 与 `F_RECON` 完全相同，故环境无法区分。

根据 UC composition theorem，若 `F_STATE`、key evolution、shuffle 和 reveal-token functionality 分别由安全协议实现，则把它们逐一替换为真实协议得到整体 mental-poker 组合安全。若只能证明 standalone NIZK，则同一 hybrid 仅适用于“一个 epoch 内按固定顺序单次调用”的 sequential composition；这时不应把结论称为 full UC。

### 7.5 “非己手牌 veto”定理

定义事件 `Veto(p,m)`：玩家 `p` 的一个 accepted package 导致牌点 `m` 在式 (3) 中被移除，但 `m∉U_p`。

**定理 5（非己手牌不可 veto，条件形式）。** 在 `A_1,A_4,A_5,A_6,A_7,A_8` 下，对任意 PPT adversary：

\[
 \Pr[Veto(p,m)]
 \leq \varepsilon_{KS}+\varepsilon_{state}+\varepsilon_{ser}.
\]

**证明。** 若 `p` 的 package 被接受，定理 2 给出某个 negative branch `C_i=Enc_P(-m_i;v_i)`。joint proof 又给出一个 `R_j` 与 `m_i` 对应的 owner-key plaintext。`D_prev` 的 exact-vector binding 将 `R_j` 识别为 `U_p` 中的 card；因此 `m_i∈U_p`。若 `R_j` 不是 `U_p`，则攻击者要么伪造 state digest（`ε_state+ε_ser`），要么伪造 joint/BG/OR proof（`ε_KS`）。若 `p` 不提交，则其贡献不存在，不能产生别人的 negative branch。□

**重要限制。** 若两个玩家的 authenticated readable sets 重叠，两个都可以生成看似合法的 negative branch；单个玩家的 V3 proof 无法证明跨玩家不相交。若 owner secret 已泄露，拥有该 secret 的调用者在密码学上就是 owner，不能再称为“非己手牌 veto”。

## 8. Lean 形式化与可复现证据

### 8.1 已机器检查的定理

| 层 | Lean 文件 | 代表性定理 | 结论 |
|---|---|---|---|
| V2 反例 | `ReconstructV2Counterexample.lean` | `misplaced_swap_satisfies_corrected_relation`, `public_randomness_reveals_branch`, `same_randomness_cross_key_sum_shape` | V2 soundness/ZK/聚合形状反例 |
| readable lineage | `ReadableCardProvenance.lean` | `lineage_is_canonical_encryption`, `authenticated_prior_hand_yields_user_readable_card` | 认证 readable 是 canonical plaintext 的 owner-key 密文 |
| V3 关系 | `ReconstructionV3.lean` | `valid_relation_complete`, `accepted_contribution_is_zero_or_negative_card`, `corrected_slot_semantics` | 完备性、逐槽语义和聚合正确性 |
| 跨密钥 proof | `ReconstructionV3JointSigma.lean` | `relation_iff_cross_key`, `sigma_speciallySound`, `sigma_perfect_hvzk` | 共享 `(sk_Q,v)` 的联合 Σ |
| slot OR | `ReconstructionV3SlotOr.lean` | `honest_accepts`, `specially_sound`, `simulate_accepts`, `perfect_hvzk_algebraic` | OR 完备性、fork 提取、HVZK |
| 端到端接口 | `ReconstructionV3Security.lean` | `completeness_under_assumptions`, `knowledge_soundness_under_assumptions`, `zero_knowledge_under_assumptions` | 明确列出生产链接义务的条件定理 |

`scripts/count_sorries.sh` 报告：总 `sorry/admit` 出现次数为 0；`lake build` 使用 `autoImplicit=false`、固定 Mathlib/VCV-io revision、5120000 max heartbeats。

### 8.2 尚未形式化的边界

以下内容仍应作为论文 assumptions 或未来工作：

1. `poker-protocol-bg` 中 exact Bayer–Groth Rust verifier/prover 的 refinement 和知识抽取；
2. shared transcript 下多组件 FS 的 ROM programming/forking；
3. Borsh/ABI/curve decoding bytes 与 Lean statement 的逐字节精化；
4. prior-state digest 与真实 poker VM 的 invariant 证明；
5. subgroup/canonical decoding 与具体 Stark/Ristretto backend 的证明；
6. adaptive corruption、网络活性和经济惩罚机制。

这张清单不是缺陷隐藏，而是形式化 TCB 的可审计声明。特别不能把 `ReconstructionV3Security` 中的 `ComponentAssumptions` 当作已经由 Lean 证明的事实。

## 9. 实现与实验复现

参考实现与 Lean 形式化公开于 [https://github.com/linqining/poker_protocol](https://github.com/linqining/poker_protocol)。代码分为 `poker-protocol-core`（曲线、ElGamal、transcript）、`poker-protocol-bg`（Bayer–Groth）、`poker-protocol-proofs`（V3 proof）、`poker_protocol`（状态机/ABI 门面）和 `poker_protocol_lean`（形式化）。生产 native dispatch 当前以 Stark curve/Poseidon 域为主；`NativeBls12381ReconstructionV3Verifier` 是历史命名，当前请求明确要求 `CurveId::StarkCurve`，不能据名称声称正在使用 BLS12-381。Ristretto 路径主要提供固定形状的 AIR/ABI submission wrapper，仓库中没有把该 wrapper 与完整 AIR verifier refinement 连接起来的生产证明；论文报告性能时必须标明曲线、transcript 和是否使用 release mode，不能把 Ristretto fixture 当作已验证的生产 benchmark。

已执行的复现命令：

```text
cargo test --workspace
cd poker_protocol_lean && lake build
cd poker_protocol_lean && bash scripts/count_sorries.sh
```

Rust workspace 的功能与安全回归测试通过；但当前 `cargo test --workspace` 仍有 4 个性能阈值测试失败（Ristretto remask/shuffle 的机器相关耗时超过 500ms，以及 BLS12-381 remask 基准超过 500ms）。这些失败不影响 V3 语义/篡改/绑定测试，但论文不能把 workspace 描述为“全部测试通过”。Lean 构建在首次运行时会固定拉取 Mathlib/VCV-io/PolyFun 等依赖；最终稿应把完整 build log 和 commit hash 作为 artifact 附件提交。

V3 目前在 `poker-protocol-proofs`、Borsh 编码、native precompile 和客户端构造路径中可执行；真实游戏状态机对 `prior_state_digest` 的生成/校验、owner identity 绑定、跨玩家 readable-set 不相交以及 deadline 后的聚合仍属于投稿前必须实现并测试的部分。顶级期刊版本应增加一个由真实 hand state 生成 digest、验证多个玩家 submission、拒绝重复 owner/重复 card 并完成下一轮 shuffle 的端到端测试；否则只能把 UC 结论写成条件定理。

对于论文实验，建议至少报告：

* `n=8,52` 时 proof bytes、prove/verify wall-clock、峰值内存；
* cross-key proof 数量 `k` 和 slot OR 数量 `n` 的线性增长；
* BG proof 的主导项与 OR proof 的 `O(n)` 项；
* Stark/Poseidon 与 Ristretto/Fiat–Shamir 的分别结果；
* partial submission 的状态转移和下一轮 shuffle 成功率。

## 10. 讨论、限制与未来工作

* **活性不是 soundness。** 恶意玩家不提交可以让自己的牌暂时留在牌组中；需要 deadline、stake 或替代玩家才能改善活性。
* **状态认证不可省略。** 若 host 只验证 proof 而不认证 `R_p` 的 lineage，调用者可以带入自选 readable ciphertext；此时“非己手牌不可 veto”不成立。
* **泄露量。** `n,k`、公钥、canonical cards、epoch 和 digest 是公开的；V3 不隐藏牌组大小和 readable 数量。
* **ROM/UC。** 完整 UC 依赖可组合 FS-NIZK；现有代码与 Lean 尚未给出该 theorem。若目标期刊要求标准模型，应替换为 CRS 下的 extractable NIZK 或给出新的 FS 证明。
* **自适应腐化。** 需要 erasure 或 non-committing encryption；本文只覆盖静态腐化。
* **多重持有。** 跨玩家 disjointness 必须由状态机 invariant 强制。未来可将 owner assignment 和不相交性一起放进递归可验证 state proof。
* **Bayer–Groth formalization。** 这是最值得补齐的形式化工作：一旦 BG exact implementation、serialization 和 FS composition 完成 refinement，条件 UC 定理可收缩为对具体 binary 的端到端定理。

## 11. 结论

V3 将 reconstruction 从“有序密文关系”提升为一个有明确语义的、可组合的证明系统：跨密钥联合证明确认 readable plaintext 的负元关系；Bayer–Groth 隐藏 readable-to-slot 映射；逐槽 OR 证明阻止错位交换；统一 aggregate-key 加密保证重建结果可继续洗牌；状态/transcript binding 防止跨局重放。最重要的安全边界是：reconstruction proof 只能证明一个玩家对其**已认证 readable 集合**的合法贡献，不能替代 prior-state lineage 和跨玩家 disjointness。

因此，针对“是否存在把非自己手牌 veto 的空间”的严格答案是：在 `D_prev` exact binding、owner key ownership、slot OR、cross-key proof、BG soundness 和跨玩家不相交性都成立时，不存在除安全误差外的非己手牌 veto；若任一状态假设被省略，尤其是把 `user_readable_cards` 当成任意输入，则该结论失效。这个条件化结论正是本文 UC/组合安全证明和 Lean 形式化边界需要明确表达的内容。

## 附录 A：V3 关系的紧凑形式

定义 witness

\[
 W=(b_i,v_i,ι(j),r_j,π,ρ_i),
\]

其中 `ι` 单射且 `b_i=1` 当且仅当 `i` 在 `ι` 的像中。关系 `R_V3(S,W)` 为：

\[
\begin{aligned}
 C_i &= Enc_P((-b_i)m_i;v_i), && i<n,\\
 R_j &= Enc_Q(m_{ι(j)};r_j), && j<k,\\
 S_j &= Enc_P(-m_{ι(j)};u_j), && j<k,\\
 C_i &= ReEnc_P((S\|Z)_{π(i)};ρ_i), && i<n.
\end{aligned}
\]

其中 `Z` 为公开的 `Enc_P(0;l+1)` padding。V3 verifier 不直接看到 `b,ι,π,v,u,r`；它验证这些关系的 NIZK 编码。

## 附录 B：证明错误事件的归约表

| 事件 | 归约目标 |
|---|---|
| accepted contribution plaintext 不是 `0/-m_i` | slot OR knowledge soundness / FS forking |
| negative contribution 不是 readable plaintext 的负元 | joint cross-key special soundness |
| 输出不是输入的隐藏置换 | Bayer–Groth knowledge soundness |
| readable 属于错误 state/玩家 | prior-state digest/serialization binding |
| 同一牌被两名玩家同时移除 | cross-player disjointness invariant |
| V3 proof 跨 epoch 重放 | transcript `context/epoch/prior_state` binding |
| observer 从 proof 学到 branch/mapping | OR/BG/joint ZK 或 ElGamal IND-CPA |
| readable plaintext 从 `c1,c2` 被恢复 | fresh-DLog/诚实 shuffle rerandomizer |

## 附录 C：建议提交期刊时附带的 artifact

1. 固定 commit hash、Rust toolchain、Lean toolchain 和 dependency lockfiles；
2. `cargo test --workspace` 完整输出；
3. `lake build` 和 `count_sorries.sh` 完整输出；
4. BG、cross-key、slot OR 的 proof-size/时间 CSV；
5. V2 三个反例和 V3 对应拒绝测试的最小可运行脚本；
6. 一份将 `F_RECON`、`F_STATE` 和 FS-NIZK assumptions 形式化为 machine-readable game 的补充材料。

## 参考文献

* R. Canetti. “Universally Composable Security: A New Paradigm for Cryptographic Protocols.” FOCS 2001; extended journal version, 2001/2004.
* S. Bayer and J. Groth. “Efficient Zero-Knowledge Argument for Correctness of a Shuffle.” EUROCRYPT 2012, LNCS 7237.
* C.-P. Schnorr. “Efficient Identification and Signatures for Smart Cards.” CRYPTO 1989, LNCS 435.
* D. Chaum and T. P. Pedersen. “Wallet Databases with Observers.” CRYPTO 1992, LNCS 740.
* R. Cramer, I. Damgård, and B. Schoenmakers. “Proofs of Partial Knowledge and Simplified Design of Witness Hiding Protocols.” CRYPTO 1994, LNCS 839.
* A. Fiat and A. Shamir. “How to Prove Yourself: Practical Solutions to Identification and Signature Problems.” CRYPTO 1986, LNCS 263.
* J. Castellà-Roca, F. Sebé, and J. Domingo-Ferrer. “Dropout-Tolerant TTP-Free Mental Poker.” TrustBus 2005, LNCS 3592, pp. 30–40.
* 项目实现与形式化 artifact：`poker-protocol-proofs`、`poker_protocol_lean`（本文代码基线）。

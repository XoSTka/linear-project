# ต้นฉบับ LaTeX ของรูปสูตร

รูป `f01.png` ถึง `f17.png` เรนเดอร์จาก LaTeX ด้านล่างด้วย KaTeX ถ้าต้องแก้สูตร ให้แก้ข้อความนี้แล้วเรนเดอร์ใหม่ด้วยเครื่องมือ LaTeX ใดก็ได้

## f01
```latex
A = U\,\Sigma\,V^{T} = \sum_{i}\sigma_i\,u_i\,v_i^{T},\qquad \sigma_1\ge\sigma_2\ge\dots\ge 0
```

## f02
```latex
\|A\|_F^{2}=\sum_{i,j}a_{ij}^{2}=\sum_i \sigma_i^{2}
```

## f03
```latex
\sigma_i=\sqrt{\lambda_i},\quad A^{T}A\,v_i=\lambda_i v_i,\quad u_i=\frac{A\,v_i}{\sigma_i}
```

## f04
```latex
\mathrm{MSE}=\frac{1}{N}\sum (a-b)^2,\qquad \mathrm{PSNR}=10\log_{10}\frac{255^{2}}{\mathrm{MSE}}\ \text{dB}
```

## f05
```latex
\mathrm{NCC}(W,W^{*})=\frac{\langle W,W^{*}\rangle}{\|W\|\,\|W^{*}\|},\qquad \mathrm{BER}=\frac{\text{wrong bits}}{\text{all bits}}
```

## f06
```latex
q=\left\lfloor\frac{\sigma}{\Delta}\right\rfloor,\qquad \text{bit}=q \bmod 2
```

## f07
```latex
\sigma' = \left(q'+\tfrac12\right)\Delta,\quad q' = \text{nearest interval with } q' \bmod 2 = \text{bit}
```

## f08
```latex
\text{capacity}=\left\lfloor\frac{h}{b}\right\rfloor\left\lfloor\frac{w}{b}\right\rfloor\ \text{bits}
```

## f09
```latex
\text{pos}=\frac{\hat\sigma-u}{\Delta}\bmod 1,\qquad \text{margin}=\min(\text{pos},\,1-\text{pos})\ \ge\ 0.25
```

## f10
```latex
q_i=\left\lfloor\frac{\sigma_i-u_i}{\Delta}\right\rfloor,\quad \text{bit}_i=q_i \bmod 2,\quad u_i\in[0,2\Delta)\ \text{from PBKDF2(key)}
```

## f11
```latex
\begin{gathered}\text{frame}=\underbrace{\text{length}}_{16\text{ bit}}\ \Vert\ \underbrace{\text{CRC-16}(\text{length}\Vert\text{text})}_{16\text{ bit}}\ \Vert\ \underbrace{\text{UTF-8 text}}_{8\times\text{bytes}}\\ \text{bits}=32+8\times\text{bytes}\end{gathered}
```

## f12
```latex
G=[\,I_4\ \vert\ P\,],\quad H=[\,P^{T}\ \vert\ I_3\,],\quad G H^{T}\equiv 0 \pmod 2
```

## f13
```latex
c = d\,G \bmod 2,\qquad s = H\,r^{T} \bmod 2
```

## f14
```latex
A=U S V^{T},\quad D=S+\alpha W,\quad D=U_w S_w V_w^{T},\quad A_w=U\,S_w\,V^{T}
```

## f15
```latex
D^{*}=U_w\,\mathrm{diag}(\sigma^{*})\,V_w^{T},\qquad W^{*}=\frac{D^{*}-S}{\alpha}
```

## f16
```latex
\text{shift}=\cos\big(\sigma^{*}-S,\ S_w-S\big)=\frac{\langle \sigma^{*}-S,\ S_w-S\rangle}{\|\sigma^{*}-S\|\ \|S_w-S\|}
```

## f17
```latex
\mathrm{AUC}=P\big(\text{score}_{\text{marked}}>\text{score}_{\text{never marked}}\big)+\tfrac12 P(\text{tie})
```


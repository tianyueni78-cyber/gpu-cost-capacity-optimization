import ProductClient from "./product-client";

const PRODUCTS = {
  "gpu-data": ["GPU Data", "上传与审计资源、用量、账单和 SLA 数据。"],
  "gpu-optimize": ["GPU Optimize", "在已确认约束下生成容量调整方案。"],
  "gpu-improve": ["GPU Improve", "跟踪已批准行动并验证实际收益。"],
  "gpu-forecast": ["GPU Forecast", "生成需求区间、容量缺口与采购计划。"],
};

export function generateStaticParams() {
  return Object.keys(PRODUCTS).map(slug => ({ slug }));
}

export default async function ProductPage({ params }) {
  const { slug } = await params;
  const product = PRODUCTS[slug];
  if (!product) return <main><h1>产品不存在</h1><a href="/">返回工作台</a></main>;
  return <main><section className="panel"><p className="eyebrow">PRODUCT ENTRY</p>
    <h1>{product[0]}</h1><p>{product[1]}</p>
    <p>当前通过受控独立页面接入；计算核心保持原样。</p>
    <ProductClient slug={slug} />
    <a href="/">← 返回工作台</a>
  </section></main>;
}

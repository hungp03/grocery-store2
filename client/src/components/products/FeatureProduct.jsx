import React, { useState, useEffect } from "react";
import { ProductBanner, ProductCard } from "@/components";
import { apiGetProducts, apiRecommendProductForUser } from "@/apis";

const FeatureProduct = ({ flag = 'new' }) => {
  const [products, setProducts] = useState(null);

  const fetchProduct = async () => {
    let response;
    if (flag === "new") {
      response = await apiGetProducts({ page: 1, size: 12, sort: "createdAt,desc" });
    } else if (flag === "recommendation") {
      response = await apiRecommendProductForUser();
    }
    //console.log(response)
    if (response.statusCode === 200) {
      setProducts(flag === "new" ? response.data.result : response.data);
    }
  };

  useEffect(() => {
    fetchProduct();
  }, [flag]);


  return (
    <div className="w-main">
      <h2 className="text-[20px] uppercase font-semibold py-[10px] border-b-4 border-main">
        {flag === "new" ? 'Sản phẩm mới': 'Có thể bạn sẽ thích'}
      </h2>

      <div className="grid grid-cols-6 gap-4 mt-4">
        {products?.map((e) => (
          <ProductCard key={e.id} productData={e} />
        ))}
      </div>
      {flag === "new" ? <ProductBanner /> : null}
    </div>
  );
};

export default FeatureProduct;

import React, { useState, useEffect } from 'react';
import { message } from 'antd';
import { useParams, useSearchParams, useNavigate, createSearchParams } from 'react-router-dom';
import { Breadcrumb, ProductCard, Pagination } from '@/components';
import { apiFetchRecommendSearchProduct } from '@/apis';
import Masonry from 'react-masonry-css';
import { v4 as uuidv4 } from 'uuid';
import { ClipLoader } from "react-spinners";
import icons from '@/utils/icons';

const { IoCloseSharp } = icons;
const breakpointColumnsObj = {
    default: 5,
    1100: 4,
    700: 3,
    500: 2
};

const override = {
    display: "block",
    margin: "0 auto",
};

const ProductRecommendation = () => {
    const [products, setProducts] = useState([]);
    const [params] = useSearchParams();
    const { word } = useParams();
    const [isLoading, setIsLoading] = useState(true);
    const navigate = useNavigate();

    const getPageTitle = () => {
        return word ? `Tìm kiếm đề xuất cho "${word}"` : "Tìm kiếm";
    };

    const [paginationMeta, setPaginationMeta] = useState({ page: 1, pageSize: 10, pages: 1, total: 0 });

    const fetchRecommendedProducts = async () => {
        const page = parseInt(params.get('page')) || 1;
        const pagesize = 10;

        try {
            setIsLoading(true);
            const response = await apiFetchRecommendSearchProduct(word, page, pagesize);
            if (response.statusCode === 200) {
                setProducts(response.data.result);
                setPaginationMeta(response.data.meta);
            } else {
                throw new Error('Error fetching recommended products');
            }
        } catch (error) {
            console.error('Error fetching recommended products:', error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchRecommendedProducts();
    }, [params, word]);

    const handlePagination = (page) => {
        const queries = {};
        for (let [key, value] of params.entries()) {
            queries[key] = value;
        }
        if (page) queries.page = page;

        const searchParams = createSearchParams(queries).toString();

        navigate({
            pathname: `/products/recommendation/${word}`,
            search: `?${searchParams}`,
        });
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            message.info({
                content: (
                    <div style={{ display: 'flex', flexDirection: 'column', position: 'relative', paddingRight: '30px' }}>
                        <span>
                            Không vừa ý với hệ thống đề xuất!
                        </span>
                        <span
                            onClick={handleBackToNormalSearch}
                            style={{
                                cursor: 'pointer',
                                color: '#007bff',
                                fontWeight: 'bold',
                            }}
                        >
                            Tìm với chế độ thông thường?
                        </span>
                        <button
                            onClick={() => message.destroy('recommendationMessage')}
                            style={{
                                position: 'absolute',
                                top: '5px',
                                right: '5px',
                                background: 'transparent',
                                border: 'none',
                                color: '#ff0000',
                                cursor: 'pointer',
                                fontSize: '18px',
                                zIndex: 1001,
                            }}
                        >
                            <IoCloseSharp />
                        </button>
                    </div>
                ),
                duration: 15, // 15s auto hide
                key: 'recommendationMessage',
                className: 'custom-message',
                style: {
                    marginTop: '175px',
                    right: '10px',
                    position: 'fixed',
                    zIndex: 1000,
                    animation: 'slideDown 1s ease-out',
                    padding: '15px',
                    maxWidth: '350px',
                }
            });
        }, 1000);

        return () => {
            clearTimeout(timer);
            message.destroy('recommendationMessage');
        };
    }, [word]); 

    const handleBackToNormalSearch = () => {
        navigate({
            pathname: '/products',
            search: `?search=${word}`, // Redirect to the search page with the current search term
        });
        message.destroy('recommendationMessage'); // Close the message once the user clicks the button
    };

    return (
        <div className='w-full'>
            <div className='h-20 flex justify-center items-center bg-gray-100'>
                <div className='w-main'>
                    <h3 className='font-semibold uppercase'>{getPageTitle()}</h3>
                    <Breadcrumb />
                </div>
            </div>
            <div className='mt-8 w-main m-auto'>
                {isLoading ? (
                    <div className="flex items-center justify-center h-[400px]">
                        <ClipLoader
                            size={50}
                            color={"#123abc"}
                            loading={isLoading}
                            cssOverride={override}
                            aria-label="Loading Recommended Products"
                        />
                    </div>
                ) : products?.length > 0 ? (
                    <Masonry
                        breakpointCols={breakpointColumnsObj}
                        className="my-masonry-grid flex mx-0"
                        columnClassName="my-masonry-grid_column mb-[-20px]"
                    >
                        {products.map((e) => (
                            <ProductCard key={uuidv4()} productData={e} />
                        ))}
                    </Masonry>
                ) : (
                    <div className="flex items-center justify-center h-[200px] text-gray-500">
                        Không có sản phẩm để đề xuất
                    </div>
                )}
            </div>

            {paginationMeta.pages > 1 && (
                <div className='w-main m-auto my-4 flex justify-center'>
                    <Pagination
                        totalPage={paginationMeta.pages}
                        currentPage={paginationMeta.page}
                        totalProduct={paginationMeta.total}
                        pageSize={paginationMeta.pageSize}
                        onPageChange={handlePagination}
                    />
                </div>
            )}
        </div>
    );
};

export default ProductRecommendation;

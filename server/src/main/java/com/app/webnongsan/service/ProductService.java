package com.app.webnongsan.service;

import com.app.webnongsan.domain.Category;
import com.app.webnongsan.domain.Product;
import com.app.webnongsan.domain.response.PaginationDTO;
import com.app.webnongsan.domain.response.product.ResProductDTO;
import com.app.webnongsan.domain.response.product.SearchProductDTO;
import com.app.webnongsan.repository.CategoryRepository;
import com.app.webnongsan.repository.ProductRepository;
import com.app.webnongsan.util.PaginationHelper;
import com.app.webnongsan.util.exception.ResourceInvalidException;
import jakarta.persistence.EntityManager;
import jakarta.persistence.criteria.*;
import lombok.AllArgsConstructor;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.io.IOException;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@AllArgsConstructor
public class ProductService {
    private final ProductRepository productRepository;
    private final CategoryRepository categoryRepository;
    private final EntityManager entityManager;
    private final RestTemplate restTemplate;
    private final String FASTAPI_URL_SEARCH_RECOMMENDED = "http://127.0.0.1:8000/search/%s";
    private final int PRODUCT_RECOMMEND_COUNT = 20;
    private final PaginationHelper paginationHelper;

    public boolean checkValidCategoryId(long categoryId) {
        return this.categoryRepository.existsById(categoryId);
    }

    public Product create(Product p) {
        return this.productRepository.save(p);
    }

    public boolean checkValidProductId(long id) {
        return this.productRepository.existsById(id);
    }

    public Product get(long id) {
        return this.productRepository.findById(id).orElse(null);
    }

    public void delete(long id) {
        this.productRepository.deleteById(id);
    }

    public PaginationDTO getAll(Specification<Product> spec, Pageable pageable) {
        Page<Product> productPage = this.productRepository.findAll(spec, pageable);
        PaginationDTO p = new PaginationDTO();
        PaginationDTO.Meta meta = new PaginationDTO.Meta();
        meta.setPage(pageable.getPageNumber() + 1);
        meta.setPageSize(pageable.getPageSize());
        meta.setPages(productPage.getTotalPages());
        meta.setTotal(productPage.getTotalElements());
        p.setMeta(meta);
        List<ResProductDTO> listProducts = productPage.getContent().stream().map(this::convertToProductDTO).toList();
        p.setResult(listProducts);
        return p;
    }

    public ResProductDTO convertToProductDTO(Product p) {
        ResProductDTO res = new ResProductDTO();
        res.setId(p.getId());
        res.setProduct_name(p.getProductName());
        res.setCategory(p.getCategory().getName());
        res.setPrice(p.getPrice());
        res.setSold(p.getSold());
        res.setQuantity(p.getQuantity());
        res.setImageUrl(p.getImageUrl());
        res.setUnit(p.getUnit());
        res.setDescription(p.getDescription());
        res.setRating(p.getRating());
        return res;
    }

    public Product findById(long id) {
        return this.productRepository.findById(id).orElse(null);
    }

    public Product update(Product p) {
        Product curr = this.findById(p.getId());
        if (curr != null) {
            curr.setProductName(p.getProductName());
            curr.setPrice(p.getPrice());
            curr.setImageUrl(p.getImageUrl());
            curr.setDescription(p.getDescription());
            curr.setQuantity(p.getQuantity());
            curr.setUnit(p.getUnit());
        }
        assert curr != null;
        return this.productRepository.save(curr);
    }

    public double getMaxPrice(String category, String productName) throws ResourceInvalidException {
        if (category != null && !category.isEmpty() && !this.categoryRepository.existsByName(category)) {
            throw new ResourceInvalidException("Category không tồn tại");
        }
        return this.productRepository.getMaxPriceByCategoryAndProductName(category, productName);
    }

    public PaginationDTO search(Specification<Product> spec, Pageable pageable) {
        Page<SearchProductDTO> productPage = this.searchProduct(spec, pageable);
        return this.paginationHelper.buildPaginationDTO(productPage);
    }

    public Page<SearchProductDTO> searchProduct(Specification<Product> specification, Pageable pageable) {
        CriteriaBuilder cb = entityManager.getCriteriaBuilder();
        CriteriaQuery<SearchProductDTO> query = cb.createQuery(SearchProductDTO.class);
        Root<Product> productRoot = query.from(Product.class);
        Join<Product, Category> categoryJoin = productRoot.join("category");
        Predicate predicate = specification.toPredicate(productRoot, query, cb);
        if (predicate != null) {
            query.where(predicate);
        }

        query.select(cb.construct(SearchProductDTO.class,
                productRoot.get("id"),
                productRoot.get("productName"),
                productRoot.get("price"),
                productRoot.get("imageUrl"),
                categoryJoin.get("name")
        ));

        List<SearchProductDTO> resultList = entityManager.createQuery(query)
                .setFirstResult((int) pageable.getOffset())
                .setMaxResults(pageable.getPageSize())
                .getResultList();

        CriteriaQuery<Long> countQuery = cb.createQuery(Long.class);
        Root<Product> countRoot = countQuery.from(Product.class);
        countQuery.select(cb.count(countRoot));

        Predicate countPredicate = specification.toPredicate(countRoot, countQuery, cb);
        if (countPredicate != null) {
            countQuery.where(countPredicate);
        }

        Long totalCount = entityManager.createQuery(countQuery).getSingleResult();

        return new PageImpl<>(resultList, pageable, totalCount);
    }

    public List<Long> fetchSimilarIds(Long id, String apiUrl) {
        String url = String.format(apiUrl, id);
        Map<String, Object> response = restTemplate.getForObject(url, Map.class);

        return Optional.ofNullable((List<Integer>) response.get("data"))
                .orElse(Collections.emptyList())
                .stream()
                .map(Integer::longValue)
                .collect(Collectors.toList());
    }

    public List<SearchProductDTO> getSimilarProducts(Long id, String apiUrl) {
        // Lấy danh sách các ID sản phẩm tương tự
        List<Long> ids = fetchSimilarIds(id, apiUrl);
        if (ids.isEmpty()) {
            return Collections.emptyList();
        }
        List<SearchProductDTO> res = productRepository.findByIdInList(ids);

        Map<Long, SearchProductDTO> productMap = res.stream()
                .collect(Collectors.toMap(SearchProductDTO::getId, Function.identity()));

        return ids.stream()
                .map(productMap::get)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());
    }

    public List<Long> fetchSearchProductIds(String word, int page, int pagesize) {
        String url = String.format(FASTAPI_URL_SEARCH_RECOMMENDED, word) + "?page=" + page + "&pagesize=" + pagesize;

        Map<String, Object> response = restTemplate.getForObject(url, Map.class);

        return Optional.ofNullable((List<Integer>) response.get("data"))
                .orElse(Collections.emptyList())
                .stream()
                .map(Integer::longValue)
                .collect(Collectors.toList());
    }


    public Page<SearchProductDTO> getSearchRecommendProducts(String word, int page, int pageSize) {
        List<Long> ids = fetchSearchProductIds(word, page, pageSize);
        if (ids.isEmpty()) {
            return new PageImpl<>(Collections.emptyList(), PageRequest.of(page - 1, pageSize), PRODUCT_RECOMMEND_COUNT);
        }

        List<SearchProductDTO> res = productRepository.findByIdInList(ids);

        // Tạo Map để truy vấn nhanh theo ID
        Map<Long, SearchProductDTO> productMap = res.stream()
                .collect(Collectors.toMap(SearchProductDTO::getId, Function.identity()));

        List<SearchProductDTO> sortedRes = ids.stream()
                .map(productMap::get)
                .filter(Objects::nonNull)
                .collect(Collectors.toList());

        return new PageImpl<>(sortedRes, PageRequest.of(page - 1, pageSize), PRODUCT_RECOMMEND_COUNT);
    }


    public PaginationDTO searchWithRecommend(String word, int page, int pageSize) {
        return this.paginationHelper.buildPaginationDTO(getSearchRecommendProducts(word, page, pageSize));
    }

}

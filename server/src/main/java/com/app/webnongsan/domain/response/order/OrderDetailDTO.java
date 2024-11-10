package com.app.webnongsan.domain.response.order;

import jakarta.persistence.Transient;
import lombok.AllArgsConstructor;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
public class OrderDetailDTO {
    private long productId;
    private String productName;
    private int quantity;
    private Double unit_price;

    private String imageUrl;
    private String category;

    private long orderId;
    private Instant orderTime;
    private int status;
    @Transient
    private String formattedPrice;
    // Constructor không bao gồm formattedPrice để Hibernate sử dụng
    public OrderDetailDTO(long productId, String productName, int quantity, Double unit_price,
                          String imageUrl, String category, long orderId, Instant orderTime, int status) {
        this.productId = productId;
        this.productName = productName;
        this.quantity = quantity;
        this.unit_price = unit_price;
        this.imageUrl = imageUrl;
        this.category = category;
        this.orderId = orderId;
        this.orderTime = orderTime;
        this.status = status;
    }
}

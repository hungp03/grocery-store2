
package com.app.webnongsan.service;

import com.app.webnongsan.domain.Product;
import com.app.webnongsan.domain.response.product.ResProductDTO;
import com.app.webnongsan.repository.CategoryRepository;
import com.app.webnongsan.repository.ProductRepository;
import lombok.AllArgsConstructor;

import javax.swing.JFileChooser;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.io.FileOutputStream;
import java.lang.String;

@Service
@AllArgsConstructor
public class DataExportService {
    private final ProductRepository productRepository;

    public byte[] exportDataToExcel() throws IOException {
        Workbook workbook = new XSSFWorkbook();
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            // Tạo sheet và ghi dữ liệu vào workbook
            Sheet sheet = workbook.createSheet("Products");

            // Tiêu đề cột
            List<String> headers = List.of("ID", "Category", "Name", "Quantity", "Price", "Sold", "Unit", "Rating", "Description");
            Row headerRow = sheet.createRow(0);
            for (int i = 0; i < headers.size(); i++) {
                headerRow.createCell(i).setCellValue(headers.get(i));
            }

            // Thêm dữ liệu (ví dụ)
            List<Product> products = productRepository.findAll(); // Lấy từ DB
            int rowIndex = 1;
            for (Product p : products) {
                Row row = sheet.createRow(rowIndex++);
                row.createCell(0).setCellValue(p.getId());
                row.createCell(1).setCellValue(p.getCategory().getName());
                row.createCell(2).setCellValue(p.getProductName());
                row.createCell(3).setCellValue(p.getQuantity());
                row.createCell(4).setCellValue(p.getPrice());
                row.createCell(5).setCellValue(p.getSold());
                row.createCell(6).setCellValue(p.getUnit());
                row.createCell(7).setCellValue(p.getRating());
                row.createCell(8).setCellValue(p.getDescription());
            }

            // Ghi workbook ra byte array
            workbook.write(outputStream);
            return outputStream.toByteArray();
        } finally {
            workbook.close();
        }
    }
}

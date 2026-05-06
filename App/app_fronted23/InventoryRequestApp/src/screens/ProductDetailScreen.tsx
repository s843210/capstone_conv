import React from 'react';
import {SafeAreaView, Text, View, Pressable} from 'react-native';
import {ProductDetailScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

export default function ProductDetailScreen({navigation, route}: ProductDetailScreenProps) {
  const {product} = route.params;

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>{product.name}</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>카테고리: {product.category}</Text>
        <Text style={styles.cardMeta}>상품 설명: {product.description}</Text>
        <Text style={styles.cardMeta}>
          재고 상태: {product.stock > 0 ? `${product.stock}개 남음` : '품절'}
        </Text>
        {product.stock <= 0 && (
          <Text style={styles.mutedText}>현재 품절된 상품입니다.</Text>
        )}
      </View>
      <Pressable
        style={[styles.primaryBtn, product.stock <= 0 && styles.primaryBtnDisabled]}
        onPress={() => navigation.navigate('RequestQty', {product})}
        disabled={product.stock <= 0}>
        <Text style={styles.primaryBtnText}>{product.stock > 0 ? '수량 요청하기' : '품절 상품'}</Text>
      </Pressable>
    </SafeAreaView>
  );
}

import React, {useState} from 'react';
import {SafeAreaView, Text, TextInput, Pressable, Alert} from 'react-native';
import {RequestItem, RequestQtyScreenProps} from '../types';
import {styles} from '../styles/commonStyles';
import {MAX_REQUEST_QTY} from '../data/appConstants';

type Props = RequestQtyScreenProps & {
  addRequest: (item: RequestItem) => Promise<boolean>;
};

export default function RequestQtyScreen({navigation, route, addRequest}: Props) {
  const {product} = route.params;
  const [qty, setQty] = useState('1');

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>요청 수량 입력</Text>
      <Text style={styles.subtitle}>요청 상품: {product.name}</Text>
      <Text style={styles.mutedText}>최대 요청 수량은 {MAX_REQUEST_QTY}개입니다.</Text>
      <TextInput
        keyboardType="number-pad"
        value={qty}
        onChangeText={setQty}
        style={styles.input}
      />

      <Pressable
        style={styles.primaryBtn}
        onPress={async () => {
          const trimmedQty = qty.trim();
          if (!trimmedQty) {
            Alert.alert('입력 오류', '요청 수량을 입력해 주세요.');
            return;
          }
          if (!/^\d+$/.test(trimmedQty)) {
            Alert.alert('입력 오류', '수량은 소수점/문자 없이 정수만 입력해 주세요.');
            return;
          }

          const num = Number(trimmedQty);
          if (!Number.isInteger(num)) {
            Alert.alert('입력 오류', '수량은 정수만 입력해 주세요.');
            return;
          }
          if (num <= 0) {
            Alert.alert('입력 오류', '수량은 1개 이상 입력해 주세요.');
            return;
          }
          if (num > MAX_REQUEST_QTY) {
            Alert.alert('입력 오류', `최대 요청 수량은 ${MAX_REQUEST_QTY}개입니다.`);
            return;
          }

          const item: RequestItem = {
            id: `r-${Date.now()}`,
            productId: product.id,
            productName: product.name,
            qty: num,
            createdAt: new Date().toLocaleString('ko-KR'),
          };

          const saved = await addRequest(item);
          if (!saved) {
            Alert.alert('저장 오류', '요청 저장 중 오류가 발생했습니다.');
            return;
          }

          navigation.navigate('RequestDone', {item});
        }}>
        <Text style={styles.primaryBtnText}>요청 접수하기</Text>
      </Pressable>
    </SafeAreaView>
  );
}

